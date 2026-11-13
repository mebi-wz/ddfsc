import json
import logging
from pathlib import Path

from odoo import Command


_logger = logging.getLogger(__name__)


LEGACY_TO_VERA = {
    "101000": "1330",
    "101300": "1100",
    "101401": "1073",
    "101402": "1095",
    "101403": "1090",
    "101404": "1090",
    "101701": "1090",
    "110100": "1260",
    "110400": "1250",
    "110500": "1250",
    "121000": "1100",
    "121100": "1270",
    "122000": "1170",
    "128000": "1300",
    "131000": "1180",
    "132000": "1180",
    "141000": "1300",
    "151000": "1715",
    "191000": "1990",
    "201000": "2045",
    "201100": "2045",
    "211000": "2000",
    "211100": "2045",
    "212000": "2060",
    "230000": "2030",
    "230100": "2120",
    "230200": "2130",
    "251000": "2100",
    "252000": "2100",
    "291000": "2300",
    "301000": "3000",
    "302000": "3110",
    "400000": "4010",
    "441000": "4900",
    "442000": "4900",
    "443000": "6900",
    "450000": "4900",
    "500000": "5100",
    "600000": "6900",
    "610000": "5095",
    "611000": "1730",
    "612000": "6900",
    "620000": "6160",
    "630000": "6010",
    "641000": "6430",
    "642000": "6900",
    "643000": "4900",
    "961000": "6900",
    "962000": "8900",
    "999998": "3200",
    "999999": "3210",
}


HISTORY_MODELS = {"account.move.line", "account.analytic.line"}


def _load_design():
    path = Path(__file__).parent / "data" / "coa.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _find_account(env, company, code):
    return env["account.account"].with_company(company).with_context(active_test=False).search(
        [("code", "=", code), ("company_ids", "in", company.id)], limit=1
    )


def _upsert_accounts(env, company, design):
    result = {}
    for item in design["accounts"]:
        code = item["code"]
        account = _find_account(env, company, code)
        values = {
            "name": item["name"],
            "account_type": item["account_type"],
            "reconcile": item["account_type"] in ("asset_receivable", "liability_payable"),
            "active": True,
            "note": "Vera COA. Normal balance: %s. Required dimension(s): %s. Replaces: %s"
            % (
                item["normal_balance"] or "Not specified",
                item["required_dimensions"] or "None",
                item["replaces"] or "None",
            ),
        }
        if account:
            account.write(values)
        else:
            values.update({"code": code, "company_ids": [Command.set(company.ids)]})
            account = env["account.account"].with_company(company).create(values)
        result[code] = account
    return result


def _upsert_dimensions(env, company, design):
    plan_model = env["account.analytic.plan"].sudo().with_company(company)
    analytic_model = env["account.analytic.account"].sudo().with_company(company)
    for sequence, (plan_name, values) in enumerate(design["dimensions"].items(), start=1):
        plan = plan_model.search([("name", "=", plan_name), ("parent_id", "=", False)], limit=1)
        if plan:
            plan.write({"sequence": sequence * 10, "default_applicability": "optional"})
        else:
            plan = plan_model.create({
                "name": plan_name,
                "sequence": sequence * 10,
                "default_applicability": "optional",
            })
        for code, name in values:
            analytic_company_id = False if plan_name == "Product Line" else company.id
            analytic = analytic_model.with_context(active_test=False).search([
                ("code", "=", code),
                ("plan_id", "=", plan.id),
                ("company_id", "=", analytic_company_id),
            ], limit=1)
            vals = {"name": name, "active": True}
            if analytic:
                analytic.write(vals)
            else:
                vals.update({"code": code, "plan_id": plan.id, "company_id": analytic_company_id})
                analytic_model.create(vals)


def _remap_many2one_references(env, company, old_account, new_account):
    fields = env["ir.model.fields"].sudo().search([
        ("relation", "=", "account.account"),
        ("ttype", "=", "many2one"),
        ("store", "=", True),
    ])
    for field in fields:
        if field.model in HISTORY_MODELS or field.model not in env:
            continue
        model = env[field.model].sudo().with_company(company).with_context(active_test=False)
        if not model._auto:
            continue
        try:
            records = model.search([(field.name, "=", old_account.id)])
        except Exception:
            _logger.debug("Cannot search %s.%s during COA remap", field.model, field.name, exc_info=True)
            continue
        for record in records:
            try:
                with env.cr.savepoint():
                    record.write({field.name: new_account.id})
            except Exception:
                _logger.warning(
                    "Could not remap %s.%s record %s from %s to %s",
                    field.model, field.name, record.id, old_account.code, new_account.code,
                    exc_info=True,
                )


def _remap_many2many_references(env, company, old_account, new_account):
    fields = env["ir.model.fields"].sudo().search([
        ("relation", "=", "account.account"),
        ("ttype", "=", "many2many"),
        ("store", "=", True),
    ])
    for field in fields:
        if field.model in HISTORY_MODELS or field.model not in env:
            continue
        model = env[field.model].sudo().with_company(company).with_context(active_test=False)
        if not model._auto:
            continue
        try:
            records = model.search([(field.name, "in", old_account.id)])
        except Exception:
            continue
        for record in records:
            try:
                with env.cr.savepoint():
                    values = record[field.name] - old_account | new_account
                    record.write({field.name: [Command.set(values.ids)]})
            except Exception:
                _logger.warning(
                    "Could not remap %s.%s record %s from %s to %s",
                    field.model, field.name, record.id, old_account.code, new_account.code,
                    exc_info=True,
                )


def _remap_legacy_accounts(env, company, accounts):
    move_line_model = env["account.move.line"].sudo().with_company(company)
    for old_code, new_code in LEGACY_TO_VERA.items():
        old_account = _find_account(env, company, old_code)
        new_account = accounts[new_code]
        if not old_account or old_account == new_account:
            continue
        _remap_many2one_references(env, company, old_account, new_account)
        _remap_many2many_references(env, company, old_account, new_account)
        move_count = move_line_model.search_count([("account_id", "=", old_account.id)])
        legacy_note = (old_account.note or "") + "\nLegacy account superseded by Vera account %s." % new_code
        old_account.write({"note": legacy_note.strip(), "active": bool(move_count)})


def post_init_hook(env):
    design = _load_design()
    companies = env["res.company"].sudo().search([])
    for company in companies:
        scoped_env = env(context=dict(env.context, allowed_company_ids=company.ids))
        accounts = _upsert_accounts(scoped_env, company, design)
        _upsert_dimensions(scoped_env, company, design)
        _remap_legacy_accounts(scoped_env, company, accounts)
    _logger.info(
        "Vera COA migration complete: %s accounts, %s analytic plans",
        len(design["accounts"]), len(design["dimensions"]),
    )

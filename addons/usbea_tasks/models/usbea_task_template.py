"""Task templates for repeatable nonprofit workflows.

Each template encodes a category (program_launch, grant_report, board_meeting,
event_planning, donor_cultivation, compliance_deadline) and a checklist of
subtask names with default due-date offsets. Instantiating a template on a
task expands the checklist into Odoo subtasks.
"""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

TEMPLATE_CATEGORIES = [
    ("program_launch", "Program launch"),
    ("grant_report", "Grant report"),
    ("board_meeting", "Board meeting prep"),
    ("event_planning", "Event planning"),
    ("donor_cultivation", "Donor cultivation"),
    ("compliance_deadline", "Compliance deadline"),
]


class UsbeaTaskTemplate(models.Model):
    _name = "usbea.task.template"
    _description = "USBEA Task Template"
    _order = "category, name"
    _rec_name = "name"

    name = fields.Char(required=True)
    technical_key = fields.Char(
        required=True,
        copy=False,
        help="Stable identifier referenced from code or data (snake_case).",
    )
    category = fields.Selection(TEMPLATE_CATEGORIES, required=True)
    description = fields.Text()
    default_assignee_role = fields.Selection(
        [
            ("program_manager", "Program Manager"),
            ("grant_writer", "Grant Writer"),
            ("executive_director", "Executive Director"),
            ("treasurer", "Treasurer"),
            ("ops_manager", "Operations Manager"),
            ("any", "Anyone"),
        ],
        default="any",
    )
    default_due_offset_days = fields.Integer(
        default=14,
        help="Number of days after instantiation to set as the parent task's deadline.",
    )
    default_priority = fields.Selection(
        [("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Urgent")],
        default="1",
    )
    checklist_item_ids = fields.One2many(
        "usbea.task.checklist_item",
        "template_id",
        string="Checklist items",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "technical_key_unique",
            "UNIQUE(technical_key)",
            "Task template technical_key must be unique.",
        ),
    ]

    @api.constrains("default_due_offset_days")
    def _check_offset(self):
        for rec in self:
            if rec.default_due_offset_days < 0 or rec.default_due_offset_days > 365:
                msg = _(
                    "default_due_offset_days must be between 0 and 365 (got %s)",
                ) % rec.default_due_offset_days
                raise ValidationError(msg)

    def instantiate_on_task(self, task) -> list:
        """Apply this template to *task* — populate fields, create subtasks.

        Returns the list of created subtask records. Idempotent over checklist
        items: a checklist item already represented as a subtask (by name) is
        not duplicated. Safe to call multiple times on the same task.
        """
        self.ensure_one()
        if not task:
            msg = _("instantiate_on_task requires a target task")
            raise ValueError(msg)

        # Set parent task fields if not already set
        write_vals: dict = {"usbea_template_id": self.id}
        if not task.date_deadline and self.default_due_offset_days:
            write_vals["date_deadline"] = fields.Date.add(
                fields.Date.context_today(self), days=self.default_due_offset_days,
            )
        if self.default_priority and task.priority in (False, "0", "1"):
            # Only override if task priority is default (don't downgrade urgent)
            write_vals["priority"] = self.default_priority
        task.write(write_vals)

        # Expand checklist into subtasks
        existing_subtask_names = set(task.child_ids.mapped("name"))
        Task = self.env["project.task"]
        created = self.env["project.task"]
        today = fields.Date.context_today(self)
        for item in self.checklist_item_ids.sorted(key=lambda r: r.sequence):
            if item.name in existing_subtask_names:
                continue
            subtask_due = (
                fields.Date.add(today, days=item.due_offset_days)
                if item.due_offset_days
                else False
            )
            created |= Task.create(
                {
                    "name": item.name,
                    "description": item.description,
                    "parent_id": task.id,
                    "project_id": task.project_id.id,
                    "date_deadline": subtask_due,
                    "user_ids": task.user_ids.ids,
                },
            )
        return list(created)

    def name_get(self):
        labels = dict(TEMPLATE_CATEGORIES)
        return [(r.id, "%s · %s" % (labels.get(r.category, r.category), r.name)) for r in self]

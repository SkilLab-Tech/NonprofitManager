from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class GrantReport(models.Model):
    _name = 'usbea.grant.report'
    _description = 'Grant Compliance Report'
    _inherit = ['mail.thread']
    _order = 'due_date desc, id desc'

    name = fields.Char('Report Title', required=True)
    grant_id = fields.Many2one(
        'usbea.grant', 'Grant', required=True, ondelete='cascade',
    )
    report_type = fields.Selection([
        ('narrative', 'Narrative Report'),
        ('financial', 'Financial Report'),
        ('impact', 'Impact Report'),
        ('closeout', 'Final Closeout Report'),
    ], string='Report Type', required=True)
    due_date = fields.Date('Due Date', required=True)
    submission_date = fields.Date('Submission Date', readonly=True)
    period_start = fields.Date('Reporting Period Start')
    period_end = fields.Date('Reporting Period End')

    # Content
    narrative = fields.Html('Narrative Content')
    financial_summary = fields.Html('Financial Summary')
    impact_metrics = fields.Html('Impact Metrics')
    attachments = fields.Many2many(
        'ir.attachment', string='Attachments',
    )

    # Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('submitted', 'Submitted to Funder'),
        ('accepted', 'Accepted'),
        ('revision', 'Revision Requested'),
    ], default='draft', tracking=True, string='Status')

    submitted_by = fields.Many2one('res.users', 'Submitted By', readonly=True)
    reviewer_id = fields.Many2one('res.users', 'Reviewer')
    funder_feedback = fields.Text('Funder Feedback')

    def action_start(self):
        for report in self:
            if report.state != 'draft':
                raise UserError(_("Only draft reports can be started."))
            report.state = 'in_progress'

    def action_submit_review(self):
        for report in self:
            if report.state not in ('in_progress', 'revision'):
                raise UserError(
                    _("Only in-progress or revision reports can be submitted "
                      "for review.")
                )
            report.state = 'review'

    def action_submit_funder(self):
        for report in self:
            if report.state != 'review':
                raise UserError(
                    _("Only reviewed reports can be submitted to funder.")
                )
            report.state = 'submitted'
            report.submission_date = fields.Date.today()
            report.submitted_by = self.env.user

    def action_accept(self):
        for report in self:
            if report.state != 'submitted':
                raise UserError(
                    _("Only submitted reports can be accepted.")
                )
            report.state = 'accepted'

    def action_request_revision(self):
        for report in self:
            if report.state != 'submitted':
                raise UserError(
                    _("Only submitted reports can have revisions requested.")
                )
            report.state = 'revision'

    def action_reset_draft(self):
        for report in self:
            report.state = 'draft'

from odoo import models, fields


class RequestType(models.Model):
    _inherit = "request.type"

    website_comments_closed = fields.Boolean(
        'Are comments not available?', default=False,
        help="Disable website comments on closed requests")

    # Request type has no websitepublish url yet, so we just need
    # website_published field, thus implement it in explicit way here insetead
    # of inheriting from "website.published.mixin"
    website_published = fields.Boolean('Visible in Website', copy=False)
    website_ids = fields.Many2many('website')

    # Help message for request text
    website_request_text_help = fields.Text()
    # Custom title for request
    website_request_title = fields.Char()
    # Custom label for request text editor
    website_custom_label_editor = fields.Char()
    website_custom_congratulation_note = fields.Html()

    # Access rignts
    access_group_ids = fields.Many2many(
        'res.groups', string='Access groups',
        help="If user belongs to one of groups specified in this field,"
             " then he will be able to select this category during request"
             " creation on website, even if this category is not published."
    )

    def website_publish_button(self):
        for rec in self:
            rec.website_published = not rec.website_published

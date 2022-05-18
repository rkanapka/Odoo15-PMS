from odoo import models, fields


class RequestCategory(models.Model):
    _inherit = "request.category"

    # Request category has no websitepublish url yet, so we just need
    # website_published field, thus implement it in explicit way here insetead
    # of inheriting from "website.published.mixin"
    website_published = fields.Boolean(
        'Visible in Website', copy=False)
    website_ids = fields.Many2many('website')

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
        return True

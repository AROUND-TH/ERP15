# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    is_vehicle_used = fields.Boolean('Used Vehicle', 
        default=False,
        tracking=True
    )

    generate_number = fields.Char(
        string='Generate No.', 
        copy=False,
    )

    @api.constrains('license_plate')
    def _check_code(self):
        for vehicle in self:
            if vehicle.license_plate:
                values = self.env['fleet.vehicle'].search([('license_plate', '=', vehicle.license_plate)])
                for data in values:
                    if data.id != vehicle.id:
                        raise ValidationError(_("This 'BAH No.' are already exist !"))


    @api.model
    def _get_sequence_next(self):
        if self.is_vehicle_used:
            running_prefix = "BAU%(y)s"
            code = f"fleet.vehicle.{running_prefix}"
            sequence_next = self.env['ir.sequence'].sudo().next_by_code(code)

            if not sequence_next:
                sequence = self.env['ir.sequence'].sudo().create({
                    'company_id': self.env.company.id,
                    'name': f'Vehicle {running_prefix}',
                    'code': code,
                    'prefix': running_prefix,
                    'padding': 4,
                    'use_date_range': True,
                    'range_reset': 'yearly',
                })
                sequence_next = sequence.sudo().next_by_code(code)
        else:
            running_prefix = "BAH%(y)s"
            code = f"fleet.vehicle.{running_prefix}"
            sequence_next = self.env['ir.sequence'].sudo().next_by_code(code)

            if not sequence_next:
                sequence = self.env['ir.sequence'].sudo().create({
                    'company_id': self.env.company.id,
                    'name': f'Vehicle {running_prefix}',
                    'code': code,
                    'prefix': running_prefix,
                    'padding': 4,
                    'use_date_range': True,
                    'range_reset': 'yearly',
                })
                sequence_next = sequence.sudo().next_by_code(code)

        return sequence_next

    # @Override odoo core method create
    @api.model
    def create(self, vals):
        vehicle = super(FleetVehicle, self).create(vals)
        if not vehicle.license_plate:
            sequence = vehicle._get_sequence_next()
            if sequence:
                vehicle.update(
                    {
                        "generate_number": sequence,
                        "license_plate": sequence,
                    }
                )
        return vehicle

    # @Override odoo core method write
    def write(self, vals):
        if isinstance(self.id, int):
            change_sequence = False
            if vals.get('is_vehicle_used') or vals.get('is_vehicle_used') == False:
                vals['generate_number'] = False
                if not vals.get('license_plate'):
                    change_sequence = True

        result = super(FleetVehicle, self).write(vals)
        if isinstance(self.id, int):
            if change_sequence:
                sequence = self._get_sequence_next()
                if sequence:
                    self.update(
                        {
                            "generate_number": sequence,
                            "license_plate": sequence,
                        }
                    )
            elif not self.license_plate and (self.is_vehicle_used or self.is_vehicle_used == False):
                if not self.generate_number:
                    sequence = self._get_sequence_next()
                    if sequence:
                        self.update(
                            {
                                "generate_number": sequence,
                                "license_plate": sequence,
                            }
                        )
                else:
                    self.update({"license_plate": self.generate_number})

        return result


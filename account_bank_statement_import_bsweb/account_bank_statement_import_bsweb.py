# -*- encoding: utf-8 -*-
##############################################################################
#
#    account_bank_statement_import_csv module for Odoo
#    Copyright (C) 2016 Stein & Gabelgaard
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import unicodecsv
import re
from cStringIO import StringIO
import hashlib
from odoo.tools import ustr

import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        '''
            Copied from addons/account_bank_statement_import/account_bank_statement_import.py
            
            Purpose: Let's partner_id be used
        '''
        for st_vals in stmts_vals:
            st_vals['journal_id'] = journal.id
            if not st_vals.get('reference'):
                st_vals['reference'] = self.filename
            if st_vals.get('number'):
                #build the full name like BNK/2016/00135 by just giving the number '135'
                st_vals['name'] = journal.sequence_id.with_context(ir_sequence_date=st_vals.get('date')).get_next_char(st_vals['number'])
                del(st_vals['number'])
            for line_vals in st_vals['transactions']:
                unique_import_id = line_vals.get('unique_import_id')
                if unique_import_id:
                    line_vals['unique_import_id'] = str(journal.id) + '-' + unique_import_id

                if not line_vals.get('bank_account_id') and not line_vals.get('partner_id'):
                    # Find the partner and his bank account or create the bank account. The partner selected during the
                    # reconciliation process will be linked to the bank when the statement is closed.
                    partner_id = False
                    bank_account_id = False
                    identifying_string = line_vals.get('account_number')
                    if identifying_string:
                        partner_bank = self.env['res.partner.bank'].search([('acc_number', '=', identifying_string)], limit=1)
                        if partner_bank:
                            bank_account_id = partner_bank.id
                            partner_id = partner_bank.partner_id.id
                        else:
                            bank_account_id = self.env['res.partner.bank'].create({'acc_number': line_vals['account_number']}).id
                    line_vals['partner_id'] = partner_id
                    line_vals['bank_account_id'] = bank_account_id

        return stmts_vals
    
    @api.model
    def _get_hide_journal_field(self):
        """ Return False if the journal_id can't be provided by the parsed
        file and must be provided by the wizard.
        See account_bank_statement_import_qif """
        # pylint: disable=no-self-use
        return False
    
    @api.model
    def _prepare_csv_encoding(self):
        '''This method is designed to be inherited'''
        return 'cp1252'

    @api.model
    def _prepare_csv_date_format(self, datestr):
        '''This method is designed to be inherited'''
        if '.' in datestr:
            return '%d.%m.%Y'
        elif '-' in datestr:
            return '%Y-%m-%d'
        
        
    @api.model
    def _csv_convert_amount(self, amount_str):
        '''This method is designed to be inherited'''
        valstr = re.sub(r'[^\d,.-]', '', amount_str)
        valstrdot = valstr.replace('.', '')
        valstrdot = valstrdot.replace(',', '.')
        return float(valstrdot)
    
    @api.model
    def _csv_get_note(self, line):
        note = False
        fields = []
        for f in ['Kommentar', 'Kategori', 'Underkategori', 'Egen bilagsreference']:
            if f in line:
                fields.append(line[f])
        if fields:
            note = ' '.join(filter(None, fields))
        return note
    
    def _parse_file(self, data_file):
        """ Import a file in Danish Bank CSV format"""
        
        f = StringIO()
        f.write(data_file.lstrip())
        f.seek(0)
        transactions = []
        i = 0
        d = 0
        start_balance = end_balance = start_date_str = end_date_str = False
        vals_line = False
        company_currency_name = self.env.user.company_id.currency_id.name
        unique_hash = hashlib.sha1(bytearray(self.filename, 'utf-8') + data_file)
        # To confirm : is the encoding always latin1 ?
        date_format = '%Y-%m-%d'
        date_field = 'Seneste status'
        try:
            for line in unicodecsv.DictReader(
                    f, encoding=self._prepare_csv_encoding(), delimiter=';'):
                
                
                i += 1
                
                if i == 1:
                    # verify file format
                    _logger.info("KEYS: %s", line.keys())
                    if u'Bogført' in line.keys():
                        date_field = u'Bogført'
                    if not set([date_field, 'Kundenummer','Indbetalers navn', 'Status']).issubset(line.keys()):
                        return super(AccountBankStatementImport, self)._parse_file(data_file)
                    _logger.info('DATE %s %s', date_format, line[date_field])
                    if not date_format:
                        date_format = self._prepare_csv_date_format(line[date_field].strip())
                    
                    start_date_str = line[date_field].strip() 
                    date_dt = datetime.strptime(
                    line[date_field].strip(), date_format)
                     
                     
                if end_date_str == line[date_field].strip():
                    d += 1
                else:
                    d = 1
                _logger.info('Procsessing line: %d', i)
                partner = self.env['res.partner'].search([('ref', '=', line['Kundenummer'])])
                
                try:
                    vals_line = {
                        'date': datetime.strptime(line[date_field].strip(), date_format),
                        'name': "%s - %s %s" %(line['Indbetalers navn'], line['Status'], line['Egen Status']),
                        'unique_import_id': "%s-%s-%s-%s" % (line[date_field].strip(), line['Kundenummer'], line[u'Betalt beløb'], line[u'Status']),
                        'amount': self._csv_convert_amount(line[u'Betalt beløb']),
                        
                        'bank_account_id': False,
                        'ref' : self._csv_get_note(line),
                        'partner_id': partner[0].id if partner and len(partner) == 1 else False,
                        }
                    end_date_str = line[date_field].strip()
                    transactions.append(vals_line)
                except Exception as e:
                    raise UserError(_('Format Error\nLine %d could not be processed\n%s') % (i + 1, ustr(e)))
        except Exception as e:
            _logger.exception('Failed parse')
            raise UserError(_('File parse error:\n%s') % ustr(e))
        
    
        vals_bank_statement = {
            'name': _('BSweb %s - %s')
            % (start_date_str, end_date_str),
            'transactions': transactions,
        }
        return None, None, [vals_bank_statement]


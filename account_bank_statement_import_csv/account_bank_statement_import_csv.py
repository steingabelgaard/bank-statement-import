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
from openerp import models, fields, api, _
from openerp.exceptions import Warning as UserError
import unicodecsv
import re
from cStringIO import StringIO
import hashlib
from openerp.tools import ustr

import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

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
        return 'latin1'

    @api.model
    def _prepare_csv_date_format(self, datestr):
        '''This method is designed to be inherited'''
        if '.' in datestr:
            return '%d.%m.%Y'
        elif '-' in datestr:
            return '%d-%m-%Y'
        
        
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
    
    @api.model
    def _parse_file(self, data_file):
        """ Import a file in Danish Bank CSV format"""
        
        f = StringIO()
        f.write(data_file.lstrip())
        f.seek(0)
        transactions = []
        unique_ids = {}
        notifications = []
        i = 0
        d = 0
        start_balance = end_balance = start_date_str = end_date_str = False
        vals_line = False
        company_currency_name = self.env.user.company_id.currency_id.name
        unique_hash = hashlib.sha1(bytearray(self.filename, 'utf-8') + data_file)
        # To confirm : is the encoding always latin1 ?
        date_format = False
        date_field = 'Dato'
        text_field = 'Tekst'
        bal_field = 'Saldo'
        amount_field = u'Beløb'
        try:
            for line in unicodecsv.DictReader(
                    f, encoding=self._prepare_csv_encoding(), delimiter=';'):
                
                
                i += 1
                
                if i == 1:
                    # verify file format
                    _logger.info("KEYS: %s", line.keys())
                    # Nordea
                    if u'Bogført' in line.keys():
                        date_field = u'Bogført'
                    # Danske Bank Erhverv
                    if u'Bogført dato' in line.keys():
                        date_field = u'Bogført dato'
                    if u'Beløb i DKK' in line.keys():
                        amount_field = u'Beløb i DKK'
                    if u'Bogført saldo i DKK' in line.keys():
                        bal_field = u'Bogført saldo i DKK'
                    _logger.info('FILE FIELDS: %s %s %s %s', date_field, text_field, bal_field, amount_field)    
                    if not set([date_field, text_field, bal_field, amount_field]).issubset(line.keys()):
                        return super(AccountBankStatementImport, self)._parse_file(data_file)
                    if not date_format:
                        date_format = self._prepare_csv_date_format(line[date_field].strip())
                    
                    start_date_str = line[date_field].strip() 
                    date_dt = datetime.strptime(
                    line[date_field].strip(), date_format)
                    start_saldo = self._csv_convert_amount(line[bal_field].strip())
                    start_amount = self._csv_convert_amount(line[amount_field].strip())
                    start_balance =  start_saldo - start_amount 
                     
                if end_date_str == line[date_field].strip():
                    d += 1
                else:
                    d = 1
                _logger.info('XXProcsessing line: %d', i)
                try:
                    if line[date_field] in ['Afsender', 'Meddelelse', 'Kreditors identifikation af modtager']:
                        # info line to be attached to previous line
                        if transactions[-1]['note']:
                            transactions[-1]['note'] = '%s\n%s: %s' % (transactions[-1]['note'], line[date_field], line[u'Valør'])
                        else:
                            transactions[-1]['note'] = '%s: %s' % (line[date_field], line[u'Valør'])
                        continue
                    if line[date_field] == '': 
                        # info line to be attached to previous line
                        if line[u'Valør'] is not None:
                            if transactions[-1]['note']:
                                transactions[-1]['note'] = '%s\n%s' % (transactions[-1]['note'], line[u'Valør'])
                            else:
                                transactions[-1]['note'] = '%s' % (line[u'Valør'])
                        continue
                    partner = False
                    ref = False
                    txparts = line[text_field].split()
                    if txparts:
                        if len(txparts) > 1:
                            # Add the whole text as search
                            txparts.append(line[text_field])
                            
                        domain = []
                        for t in txparts:
                            if len(t) > 1:
                                domain += [('name','=ilike', t), ('ref','=ilike', t)]
                        domain = ['|'] * (len(domain) - 1) + domain
                        partner = self.env['res.partner'].search(domain)
                        for t in txparts:
                            if '/' in t and len(t) > 3:
                                ref = t
                                break

                    unique_import_id = "%d-%s-%s-%s-%s" % (self.journal_id.id, line[date_field].strip(), line[text_field], line[amount_field], line[bal_field])
                    if unique_import_id in unique_ids:
                        prev_line_no = unique_ids[unique_import_id]
                        prev_line_id = unique_import_id
                        unique_import_id = unique_import_id + '-%d' % i
                        unique_ids_list = [prev_line_id,unique_import_id]
                        notifications += [{
                            'type': 'warning',
                            'message': _("Line %d and %d are identical:\n%s %s %0.2f - Balance: %0.2f") % (prev_line_no,
                                                                                                           i,
                                                                                                           line[date_field].strip(),
                                                                                                           line[text_field],
                                                                                                           self._csv_convert_amount(line[amount_field]), 
                                                                                                           self._csv_convert_amount(line[bal_field])
                                                                                                           ),
                            'details': {
                                'name': _('Identical imported items'),
                                'model': 'account.bank.statement.line',
                                'unique_ids': unique_ids_list,
                                },
                            }]
                    vals_line = {
                        'date': datetime.strptime(line[date_field].strip(), date_format),
                        'name': line[text_field],
                        'unique_import_id': unique_import_id,
                        'amount': self._csv_convert_amount(line[amount_field]),
                        'line_balance': self._csv_convert_amount(line[bal_field]),
                        'bank_account_id': False,
                        'note' : self._csv_get_note(line),
                        'ref' : ref,
                        'partner_id': partner[0].id if partner else False,
                        }
                    unique_ids[unique_import_id] = i
                    end_date_str = line[date_field].strip()
                    end_balance = self._csv_convert_amount(line[bal_field])
                    end_amount = self._csv_convert_amount(line[amount_field])
                    _logger.info("vals_line = %s" % vals_line)
                    transactions.append(vals_line)
                except:
                    _logger.exception('Failed line %d', (i+1))
                    raise UserError(_('Format Error\nLine %d could not be processed') % (i + 1))
        except Exception as e:
            raise UserError(_('File parse error:\n%s') % ustr(e))
        
        if start_date_str and datetime.strptime(start_date_str, date_format) > datetime.strptime(end_date_str, date_format):
            #swap start / end
            _logger.debug("Swapper start/end: %s %s", end_balance, end_amount)
            swap_date = start_date_str
            start_date_str = end_date_str
            end_date_str = swap_date
            start_balance = end_balance - end_amount
            end_balance = start_saldo 

        vals_bank_statement = {
            'name': _('%s/%s-%s')
            % (self.journal_id.code, start_date_str, end_date_str),
            'balance_start': start_balance,
            'balance_end_real': end_balance,
            'transactions': transactions,
            'notifications': notifications,
        }
        if end_date_str:
            end_date = datetime.strptime(end_date_str, date_format)
            vals_bank_statement['date'] = end_date
            periods = self.env['account.period'].find(dt=end_date)
            if periods:
                vals_bank_statement['period_id'] = periods[0].id 
        _logger.debug("vals_stmt = %s" % vals_bank_statement)
        return None, None, [vals_bank_statement]


class AccountBankStatementLine(models.Model):
    """Extend model account.bank.statement.line."""
    # pylint: disable=too-many-public-methods
    _inherit = "account.bank.statement.line"
    
    line_balance = fields.Float(digits_compute=dp.get_precision('Account'))

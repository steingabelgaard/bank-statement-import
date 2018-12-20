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

{
    'name': 'Import CSV Bank Statements',
    'version': '0.1',
    'license': 'AGPL-3',
    'author': 'Stein & Gabelgaard',
    'website': 'http://www.steingabelgaard.dk',
    'summary': 'Import CSV files as Bank Statements in Odoo',
    'description': """
Danish CSV Bank Statement import

Required fields:
 - Dato
 - Tekst
 - Beløb
 - Saldo
 
Optional fields (goes into the ref field)
 - Kommentar
 - Kategori
 - Underkategori
 - Egen bilagsreference
 """,

    'depends': [
        'account_bank_statement_import'
        ],
    
    'data': [],
    'installable': True,
}
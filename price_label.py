#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from reportlab.pdfgen import canvas
from reportlab.lib import units
from reportlab.lib import pagesizes
from reportlab.graphics.barcode import code128
import base64

from trytond.report import Report
from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard
from trytond.transaction import Transaction
from trytond.pool import Pool


class Job(ModelSQL, ModelView):
    _name = 'pos_price_label.job'

    name = fields.Char('Name', size=None, required=True, select=1)
    products = fields.Many2Many('pos_price_label.job-entry-rel', 'job',
            'product', 'Products')
    finished = fields.Boolean('Finished')

    def __init__(self):
        super(Job, self).__init__()
        self._order += [('create_date', 'DESC')]

    def default_user(self):
        return Transaction().user

    def search(self, domain, offset=0, limit=None, order=None, count=False):
        Transaction().set_context(active_test=False)
        return super(Job, self).search(domain, offset, limit, order, count)

Job()


class JobEntry(ModelSQL, ModelView):
    _name = 'pos_price_label.job-entry-rel'

    job = fields.Many2One('pos_price_label.job', 'Job')
    product = fields.Many2One('product.product', 'Product')

    def search(self, domain, offset=0, limit=None, order=None, count=False):
        Transaction().set_context(active_test=False)
        return super(JobEntry, self).search(domain, offset, limit, order, count)

JobEntry()


class LabelReport(Report):
    _name = 'pos_price_label.label_report'
    _size = pagesizes.A4
    _dimension = (3, 9)
    _h_space = 2.0 * units.mm
    _v_space = 0.0


    def execute(self, ids, datas):
        pool = Pool()
        job_obj = pool.get('pos_price_label.job')
        self._data = job_obj.browse(ids[0]).products
        self._canvas = canvas.Canvas("temp_file.pdf", pagesize=self._size)
        self._h_margin = (self._size[0]
              - self._dimension[0]*Label._size[0]
              - self._h_space*(self._dimension[0]-1)) / 2.0

        self._v_margin = (self._size[1]
              - self._dimension[1]*Label._size[1]
              - self._v_space*(self._dimension[1]-1)) / 2.0
        # HACK
        self._v_margin += 1*units.mm

        self.draw(int(datas['form']['x_start']),
                int(datas['form']['y_start']))
        data = base64.encodestring(self._canvas.getpdfdata())
        return (u'pdf', data, False, u'Label')

    def draw(self, first_x=1, first_y=1):
        first_x -= 1
        first_y -= 1
        x_start = 0
        y_start = 0
        index = 0

        while index < len(self._data):
            # top left
            self._canvas.translate(0, self._size[1])
            # margins
            self._canvas.translate(self._h_margin, -self._v_margin)

            for y in range(y_start, self._dimension[1]):
                self._canvas.translate(0, -1.0 * Label._size[1])
                if(index >= len(self._data)): break

                self._canvas.saveState()
                for x in range(x_start, self._dimension[0]):
                    if(index >= len(self._data)): break

                    if(x >= first_x and y >= first_y):
                        self._canvas.saveState()
                        l = Label(self._data[index])
                        l.draw(self._canvas)
                        self._canvas.restoreState()
                        index += 1
                        first_x = 0
                        first_y = 0

                    self._canvas.translate(Label._size[0] + self._h_space, 0)

                self._canvas.restoreState()
                self._canvas.translate(0, -1.0 * self._v_space)

            self._canvas.showPage()

LabelReport()

class Label(object):
    _size = (63.5*units.mm, 29.6*units.mm)
    _font_prince = {
      'type': 'Arial',
      'size': '16',
    }
    _font_common = {
      'type': 'Arial',
      'size': '12',
    }
    _max_chars = 13

    def __init__(self, data):
        self._data = data

    def draw(self, canvas):
        # canvas.rect(0, 0, self._size[0], self._size[1])
        # HACK
        canvas.translate(3, -2)
        canvas.setFont("Helvetica-Bold", 20)
        canvas.drawString(5, 62, unicode('%.2f' % self._data.list_price)
                + u'\u20AC')
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(5, 50, self._data.name)
        canvas.setFont("Helvetica", 10)
        canvas.drawString(5, 40, '' if self._data.description is None
                else self._data.description)
        if not self._data.active:
            canvas.line(5, 35, self._size[0]-10, self._size[1]-10)
            canvas.line(self._size[0]-10, 35, 5, self._size[1]-10)

        code = self._data.code
        code = code[:self._max_chars]
        # code = (self._max_chars - len(code)) * '0' + code
        bc = code128.Code128(code,
                    humanReadable=0)
        canvas.saveState()
        canvas.scale(2.0, 1.0)
        bc.drawOn(canvas, -4.0*units.mm, 6.0 * units.mm)
        canvas.restoreState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(5*units.mm, 4*units.mm, code)


class ChooseFirstLabel(ModelView):
    _name = 'pos_price_label.choose_first_label'
    _description = 'Select first label to print on.'

    x_start = fields.Selection([(str(x), str(x)) for x in range(1, 4)],
            'First X', required=True)
    y_start = fields.Selection([(str(x), str(x)) for x in range(1, 10)],
            'First Y', required=True)

    def default_x_start(self):
        return '1'

    def default_y_start(self):
        return '1'

ChooseFirstLabel()

class PrintLabel(Wizard):
    _name = 'pos_price_label.print_labels'

    states = {
        'init': {
            'result': {
                'type': 'form',
                'object': 'pos_price_label.choose_first_label',
                'state': [
                    ('end', 'Cancel', 'tryton-cancel'),
                    ('open', 'Open', 'tryton-ok', True),
                ],
            },
        },
        'open': {
            'result': {
                'type': 'action',
                'action': '_action_print_labels',
                'state': 'end',
            },
        },
    }

    def _action_print_labels(self, data):
        pool = Pool()
        model_data_obj = pool.get('ir.model.data')
        act_report_id = model_data_obj.get_id('pos_price_label',
                'report_print_labels')
        report_obj = pool.get('ir.action.report')
        res = report_obj.read(act_report_id)
        return res

PrintLabel()


class PrintJobSelect(ModelView):
    _name = 'pos_price_label.print_job_select'
    _description = 'Select printjob.'
    printjob = fields.Many2One('pos_price_label.job', 'Printjob')

    def default_printjob(self):
        printjob_obj = Pool().get('pos_price_label.job')
        lastjob = printjob_obj.search([], limit=1, order=[
                ('create_date', 'DESC')])
        if(len(lastjob) > 0): return lastjob[0]
        return False

PrintJobSelect()

class AddProductToJob(Wizard):
    'Add product to printjob'
    _name = 'pos_price_label.add_to_printjob'

    states = {
        'init': {
            'result': {
                'type': 'form',
                'object': 'pos_price_label.print_job_select',
                'state': [
                    ('end', 'Cancel', 'tryton-cancel'),
                    ('open', 'Add', 'tryton-ok', True),
                ],
            },
        },
        'open': {
            'result': {
                'type': 'action',
                'action': '_action_add_product',
                'state': 'end',
            },
        },
    }


    def _action_add_product(self, data):
        pool = Pool()
        job_obj = pool.get('pos_price_label.job')
        pj = job_obj.browse(data['form']['printjob'])
        pje_obj = pool.get('pos_price_label.job-entry-rel')

        pj_ids = pje_obj.search([
                ('product', 'in', data['ids']),
                ('job', '=', pj.id)
            ])
        ids = set(data['ids']) - set(pj_ids)
        for id in ids:
            pje_obj.create({'job': pj.id, 'product': id})



AddProductToJob()

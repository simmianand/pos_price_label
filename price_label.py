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


__all__ = [
    'Job', 'JobEntry', 'LabelReport', 'Label', 'ChooseFirstLabel',
    'PrintLabel', 'PrintJobSelect', 'AddProductToJob'
]


class Job(ModelSQL, ModelView):
    'Job'
    __name__ = 'pos_price_label.job'

    name = fields.Char('Name', size=None, required=True, select=1)
    products = fields.Many2Many('pos_price_label.job-entry-rel', 'job',
            'product', 'Products')
    finished = fields.Boolean('Finished')

    @classmethod
    def __setup__(cls):
        super(Job, cls).__setup__()
        cls._order += [('create_date', 'DESC')]

    @staticmethod
    def default_user():
        """
        Returns the default user
        """
        return Transaction().user

    @classmethod
    def search(cls, domain, offset=0, limit=None, order=None, count=False):
        """
        Returns list of records that match the domain
        """
        Transaction().set_context(active_test=False)
        return super(Job, cls).search(domain, offset, limit, order, count)


class JobEntry(ModelSQL, ModelView):
    'Job Entry'
    __name__ = 'pos_price_label.job-entry-rel'

    job = fields.Many2One('pos_price_label.job', 'Job')
    product = fields.Many2One('product.product', 'Product')

    @classmethod
    def search(cls, domain, offset=0, limit=None, order=None, count=False):
        """
        Returns list of records that match the domain
        """
        Transaction().set_context(active_test=False)
        return super(JobEntry, cls).search(domain, offset, limit, order, count)


class LabelReport(Report):
    'Label Report'
    __name__ = 'pos_price_label.label_report'
    _size = pagesizes.A4
    _dimension = (3, 9)
    _h_space = 2.0 * units.mm
    _v_space = 0.0

    @classmethod
    def execute(cls, ids, datas):
        """
        Execute the report on record ids.

        It returns a tuple with:
            report type,
            data,
            a boolean to direct print,
            the report name

        """
        Job = Pool().get('pos_price_label.job')

        cls._data = Job(ids[0]).products
        cls._canvas = canvas.Canvas("temp_file.pdf", pagesize=cls._size)
        cls._h_margin = (cls._size[0]
              - cls._dimension[0]*Label._size[0]
              - cls._h_space*(cls._dimension[0]-1)) / 2.0

        cls._v_margin = (cls._size[1]
              - cls._dimension[1]*Label._size[1]
              - cls._v_space*(cls._dimension[1]-1)) / 2.0
        # HACK
        cls._v_margin += 1*units.mm

        cls.draw(int(datas['form']['x_start']),
                int(datas['form']['y_start']))
        data = base64.encodestring(cls._canvas.getpdfdata())
        return (u'pdf', data, False, u'Label')

    @classmethod
    def draw(cls, first_x=1, first_y=1):
        first_x -= 1
        first_y -= 1
        x_start = 0
        y_start = 0
        index = 0

        while index < len(cls._data):
            # top left
            cls._canvas.translate(0, cls._size[1])
            # margins
            cls._canvas.translate(cls._h_margin, -cls._v_margin)

            for y in range(y_start, cls._dimension[1]):
                cls._canvas.translate(0, -1.0 * Label._size[1])
                if(index >= len(cls._data)): break

                cls._canvas.saveState()
                for x in range(x_start, cls._dimension[0]):
                    if(index >= len(cls._data)): break

                    if(x >= first_x and y >= first_y):
                        cls._canvas.saveState()
                        l = Label(cls._data[index])
                        l.draw(cls._canvas)
                        cls._canvas.restoreState()
                        index += 1
                        first_x = 0
                        first_y = 0

                    cls._canvas.translate(Label._size[0] + cls._h_space, 0)

                cls._canvas.restoreState()
                cls._canvas.translate(0, -1.0 * cls._v_space)

            cls._canvas.showPage()


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

    @classmethod
    def __setup__(cls, data):
        cls._data = data

    @classmethod
    def draw(cls, canvas):
        # canvas.rect(0, 0, self._size[0], self._size[1])
        # HACK
        canvas.translate(3, -2)
        canvas.setFont("Helvetica-Bold", 20)
        canvas.drawString(5, 62, unicode('%.2f' % cls._data.list_price)
                + u'\u20AC')
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(5, 50, cls._data.name)
        canvas.setFont("Helvetica", 10)
        canvas.drawString(5, 40, '' if cls._data.description is None
                else cls._data.description)
        if not cls._data.active:
            canvas.line(5, 35, cls._size[0]-10, cls._size[1]-10)
            canvas.line(cls._size[0]-10, 35, 5, cls._size[1]-10)

        code = cls._data.code
        code = code[:cls._max_chars]
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
    __name__ = 'pos_price_label.choose_first_label'

    x_start = fields.Selection([(str(x), str(x)) for x in range(1, 4)],
            'First X', required=True)
    y_start = fields.Selection([(str(x), str(x)) for x in range(1, 10)],
            'First Y', required=True)

    @staticmethod
    def default_x_start():
        """
        Returns default for x_start
        """
        return '1'

    @staticmethod
    def default_y_start():
        """
        Returns default for x_start
        """
        return '1'


class PrintLabel(Wizard):
    'Print Label'
    __name__ = 'pos_price_label.print_labels'

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
        """
        Action foir print labels
        """
        ModelData = Pool().get('ir.model.data')
        ActionReport = Pool().get('ir.action.report')

        act_report_id = ModelData.get_id('pos_price_label',
                'report_print_labels')
        res = ActionReport.read(act_report_id)
        return res


class PrintJobSelect(ModelView):
    'Print Job Select'
    __name__ = 'pos_price_label.print_job_select'

    printjob = fields.Many2One('pos_price_label.job', 'Printjob')

    @staticmethod
    def default_printjob():
        """
        Returns default for printjob
        """
        Job = Pool().get('pos_price_label.job')

        lastjob = Job.search([], limit=1, order=[
                ('create_date', 'DESC')])
        if(len(lastjob) > 0):
            return lastjob[0]
        return False


class AddProductToJob(Wizard):
    'Add product to printjob'
    __name__ = 'pos_price_label.add_to_printjob'

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
        """
        Action for adding product
        """
        Job = Pool().get('pos_price_label.job')
        JobEntry = Pool().get('pos_price_label.job-entry-rel')

        pj = Job.browse(data['form']['printjob'])
        pj_ids = JobEntry.search([
                ('product', 'in', data['ids']),
                ('job', '=', pj.id)
            ])
        ids = set(data['ids']) - set(pj_ids)
        for id in ids:
            JobEntry.create({
                'job': pj.id,
                'product': id
            })

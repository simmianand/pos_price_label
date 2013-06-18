# -*- coding: utf-8 -*-
"""
    __init__

    pos_price_label

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from price_label import Job, JobEntry, LabelReport, Label, ChooseFirstLabel, \
    PrintLabel, PrintJobSelect, AddProductToJob

def register():
    "Register classes"
    Pool.register(
        Job,
        JobEntry,
        LabelReport,
        Label,
        ChooseFirstLabel,
        PrintLabel,
        PrintJobSelect,
        AddProductToJob,
        module='pos_price_label', type_='model'
    )

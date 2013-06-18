{
    'name' : 'POS Price Label',
    'version' : '0.0.1',
    'author' : 'Max Holtzberg',
    'email': 'max@holtzberg.de',
    'website': 'http://www.tryton.org/',
    'description': 'Provides reports for printing price labels on standard '
            'label sheets.',
    'depends' : [
        'ir',
        'company',
        'product',
    ],
    'xml' : [
        'price_label.xml',
    ],
    'translation': [
    ],
}

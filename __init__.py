# -*- coding: utf-8 -*-
"""
    __init__

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
from trytond.pool import Pool
from activity_stream import NereidUser, Activity, ActivityAllowedModel


def register():
    '''
    Register models to tryton Pool.
    '''
    Pool.register(
        NereidUser,
        Activity,
        ActivityAllowedModel,
        module='nereid_activity_stream', type_='model'
    )

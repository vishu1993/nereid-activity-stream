# -*- coding: utf-8 -*-
"""
    Test activity

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
import sys
import json
import os
DIR = os.path.abspath(os.path.normpath(os.path.join(__file__,
    '..', '..', '..', '..', '..', 'trytond')))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))
from dateutil import parser

import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends
from trytond.tests.test_tryton import POOL, CONTEXT, USER, DB_NAME
from trytond.transaction import Transaction
from trytond.exceptions import UserError

from nereid.testing import NereidTestCase


class ActivityTestCase(NereidTestCase):
    '''
    Test Nereid Activity
    '''

    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid_activity_stream')
        self.activity_obj = POOL.get('nereid.activity')
        self.party_obj = POOL.get('party.party')
        self.company_obj = POOL.get('company.company')
        self.nereid_user_obj = POOL.get('nereid.user')
        self.currency_obj = POOL.get('currency.currency')
        self.activity_allowed_model_obj = POOL.get('nereid.activity.allowed_model')
        self.model_obj = POOL.get('ir.model')
        self.url_map_obj = POOL.get('nereid.url_map')
        self.language_obj = POOL.get('ir.lang')
        self.nereid_website_obj = POOL.get('nereid.website')

    def test0005views(self):
        '''
        Test views.
        '''
        test_view('nereid_activity_stream')

    def test0006depends(self):
        '''
        Test depends.
        '''
        test_depends()

    def setup_defaults(self):
        '''
        Setting Defaults for Test Nereid Activity Stream
        '''
        usd = self.currency_obj.create({
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        })
        company_id = self.company_obj.create({
            'name': 'Openlabs',
            'currency': usd
        })
        guest_user = self.nereid_user_obj.create({
            'name': 'Guest User',
            'display_name': 'Guest User',
            'email': 'guest@openlabs.co.in',
            'password': 'password',
            'company': company_id,
        })
        self.registered_user_id = self.nereid_user_obj.create({
            'name': 'Registered User',
            'display_name': 'Registered User',
            'email': 'email@example.com',
            'password': 'password',
            'company': company_id,
        })

        # Create website
        url_map_id, = self.url_map_obj.search([], limit=1)
        en_us, = self.language_obj.search([('code', '=', 'en_US')])
        self.nereid_website_obj.create({
            'name': 'localhost',
            'url_map': url_map_id,
            'company': company_id,
            'application_user': USER,
            'default_language': en_us,
            'guest_user': guest_user,
            'currencies': [('set', [usd])],
        })


        self.user_party = self.party_obj.create({
            'name': 'User1',
        })

        currency = self.currency_obj.create({
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        })

        self.company = self.company_obj.create({
            'name': 'openlabs',
            'currency': currency,
        })

        actor_party = self.party_obj.create({
            'name': 'Party1',
        })

        nereid_user_user = self.nereid_user_obj.create({
            'party': self.user_party,
            'company': self.company,
        })

        self.nereid_user_actor = self.nereid_user_obj.create({
            'party': actor_party,
            'company': self.company,
        })

        self.nereid_stream_owner = self.nereid_user_obj.create({
            'party': nereid_user_user,
            'company': self.company,
        })

    def test0010_create_activity(self):
        '''
        Creates allowed activity model and activity.
        '''
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            party_model_id, = self.model_obj.search([
                ('model', '=', 'party.party')
            ])

            activity_object = self.activity_allowed_model_obj.create({
                'name': 'Party',
                'model': party_model_id,
            })

            # Create Activity without verb
            self.assertRaises(
                UserError, self.activity_obj.create, {
                    'actor': self.nereid_user_actor,
                    'object_': 'party.party,%s' % self.user_party,
                }
            )

            # Create Activity without actor
            self.assertRaises(
                UserError, self.activity_obj.create, {
                    'verb': 'Blog post',
                    'object_': 'party.party,%s' % self.user_party,
                }
            )

            # Create Activity without object_
            self.assertRaises(
                UserError, self.activity_obj.create, {
                    'verb': 'Added a new friend',
                    'actor': self.nereid_user_actor,
                }
            )

            # Create Activity without target
            activity = self.activity_obj.create, {
                'verb': 'Added a new friend',
                'actor': self.nereid_user_actor,
                'object_': 'party.party,%s' % self.user_party,
            }

            # Create Activity with target
            activity = self.activity_obj.create({
                'verb': 'Added a new friend',
                'actor': self.nereid_user_actor,
                'object_': 'party.party,%s' % self.user_party,
                'target': 'party.party,%s' % self.user_party
            })

            user = self.nereid_user_obj.browse(self.nereid_user_actor)
            self.assert_(
                self.activity_obj.browse(activity) in \
                user.activities
            )


    def test0020_stream(self):
        '''
        Serialize Activity Stream
        '''
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party_model_id, = self.model_obj.search([
                ('model', '=', 'party.party')
            ])

            activity_object = self.activity_allowed_model_obj.create({
                'name': 'Party',
                'model': party_model_id,
            })

            # Create 3 Activities
            activity1 = self.activity_obj.create({
                'verb': 'Added a new friend',
                'actor': self.nereid_user_actor,
                'object_': 'party.party,%s' % self.user_party,
            })

            activity2 = self.activity_obj.create({
                'verb': 'Added a friend to a list',
                'actor': self.nereid_user_actor,
                'object_': 'party.party,%s' % self.user_party,
                'target': 'party.party,%s' % self.user_party,
            })

            activity3 = self.activity_obj.create({
                'verb': 'Added a new friend',
                'actor': self.nereid_user_actor,
                'object_': 'party.party,%s' % self.user_party,
            })

            with app.test_client() as c:
                # Stream Length Count
                rv = c.get('en_US/user/activity-stream')
                rv_json = json.loads(rv.data)
                self.assertEqual(rv_json['totalItems'], 3)

                # Stream Items Length
                self.assertEqual(len(rv_json['items']), 3)

                # Activity Publish Order
                pub_dates = map(
                    lambda x: parser.parse(x['published']),
                    rv_json['items'],
                )
                self.assertTrue(pub_dates[2] < pub_dates[1] < pub_dates[0])


def suite():
    '''
    Test Suite
    '''
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        ActivityTestCase)
    )
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

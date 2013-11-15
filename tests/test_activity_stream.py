# -*- coding: utf-8 -*-
"""
    Test activity

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
import sys
import json
import os
DIR = os.path.abspath(os.path.normpath(
    os.path.join(__file__, '..', '..', '..', '..', '..', 'trytond')
))
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
        self.Activity = POOL.get('nereid.activity')
        self.Party = POOL.get('party.party')
        self.Company = POOL.get('company.company')
        self.NereidUser = POOL.get('nereid.user')
        self.Currency = POOL.get('currency.currency')
        self.ActivityAllowedModel = POOL.get('nereid.activity.allowed_model')
        self.Model = POOL.get('ir.model')
        self.UrlMap = POOL.get('nereid.url_map')
        self.Language = POOL.get('ir.lang')
        self.NereidWebsite = POOL.get('nereid.website')
        self.Locale = POOL.get('nereid.website.locale')

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
        usd, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])
        company_party, = self.Party.create([{
            'name': 'Openlabs',
        }])
        company, = self.Company.create([{
            'party': company_party.id,
            'currency': usd.id
        }])
        guest_party, registered_party = self.Party.create([{
            'name': 'Guest User',
        }, {
            'name': 'Registered User',
        }])
        guest_user, = self.NereidUser.create([{
            'party': guest_party.id,
            'display_name': 'Guest User',
            'email': 'guest@openlabs.co.in',
            'password': 'password',
            'company': company.id,
        }])
        self.registered_user, = self.NereidUser.create([{
            'party': registered_party.id,
            'display_name': 'Registered User',
            'email': 'email@example.com',
            'password': 'password',
            'company': company.id,
        }])

        # Create website
        url_map, = self.UrlMap.search([], limit=1)
        en_us, = self.Language.search([('code', '=', 'en_US')], limit=1)

        self.locale_en_us, = self.Locale.create([{
            'code': 'en_US',
            'language': en_us.id,
            'currency': usd.id,
        }])
        self.NereidWebsite.create([{
            'name': 'localhost',
            'url_map': url_map.id,
            'company': company.id,
            'application_user': USER,
            'default_locale': self.locale_en_us.id,
            'guest_user': guest_user.id,
            'currencies': [('set', [usd.id])],
        }])

        self.user_party, = self.Party.create([{
            'name': 'User1',
        }])

        currency, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])

        party, = self.Party.create([{
            'name': 'openlabs',
        }])
        self.company, = self.Company.create([{
            'party': party.id,
            'currency': currency.id,
        }])

        actor_party, = self.Party.create([{
            'name': 'Party1',
        }])
        nereid_user, = self.NereidUser.create([{
            'party': self.user_party.id,
            'company': self.company.id,
            'display_name': self.user_party.rec_name
        }])

        self.nereid_user_actor, = self.NereidUser.create([{
            'party': actor_party.id,
            'company': self.company.id,
            'display_name': actor_party.rec_name
        }])

        self.nereid_stream_owner, = self.NereidUser.create([{
            'party': nereid_user.id,
            'company': self.company.id,
            'display_name': nereid_user.rec_name
        }])

    def test0010_create_activity(self):
        '''
        Creates allowed activity model and activity.
        '''
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            party_model, = self.Model.search([
                ('model', '=', 'party.party')
            ], limit=1)

            self.ActivityAllowedModel.create([{
                'name': 'Party',
                'model': party_model,
            }])

            # Create Activity without verb
            self.assertRaises(
                UserError, self.Activity.create, [{
                    'actor': self.nereid_user_actor,
                    'object_': 'party.party,%s' % self.user_party.id,
                }]
            )

            # Create Activity without actor
            self.assertRaises(
                UserError, self.Activity.create, [{
                    'verb': 'Blog post',
                    'object_': 'party.party,%s' % self.user_party.id,
                }]
            )

            # Create Activity without object_
            self.assertRaises(
                UserError, self.Activity.create, [{
                    'verb': 'Added a new friend',
                    'actor': self.nereid_user_actor,
                }]
            )

            # Create Activity without target
            activity, = self.Activity.create([{
                'verb': 'Added a new friend',
                'actor': self.nereid_user_actor,
                'object_': 'party.party,%s' % self.user_party.id,
            }])

            # Create Activity with target
            activity, = self.Activity.create([{
                'verb': 'Added a new friend',
                'actor': self.nereid_user_actor.id,
                'object_': 'party.party,%s' % self.user_party.id,
                'target': 'party.party,%s' % self.user_party.id
            }])

            self.assert_(
                activity in self.nereid_user_actor.activities
            )

    def test0020_stream(self):
        '''
        Serialize Activity Stream
        '''
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            login_data = {
                'email': 'email@example.com',
                'password': 'password',
            }

            nereid_user_model, = self.Model.search([
                ('model', '=', 'nereid.user')
            ])
            self.ActivityAllowedModel.create([{
                'name': 'User',
                'model': nereid_user_model,
            }])

            # Create 3 Activities
            self.Activity.create([{
                'verb': 'Added a new friend',
                'actor': self.registered_user,
                'object_': 'nereid.user,%s' % self.user_party.id,
            }, {
                'verb': 'Added a friend to a list',
                'actor': self.registered_user,
                'object_': 'nereid.user,%s' % self.user_party.id,
                'target': 'nereid.user,%s' % self.user_party.id,
            }, {
                'verb': 'Added a new friend',
                'actor': self.registered_user,
                'object_': 'nereid.user,%s' % self.user_party.id,
            }])

            with app.test_client() as c:
                # Login success
                rv = c.post('/login', data=login_data)
                self.assertEqual(rv.location, 'http://localhost/?locale=en_US')
                self.assertEqual(rv.status_code, 302)

                # Stream Length Count
                rv = c.get('/user/activity-stream')
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

            # Test when object_ is deleted
            new_party, = self.Party.create([{'name': 'Tarun'}])
            new_nereid_user, = self.NereidUser.create([{
                'party': new_party.id,
                'company': self.company.id,
                'display_name': new_party.name
            }])

            self.Activity.create([{
                'verb': 'Added a new friend who does not exist',
                'actor': self.registered_user,
                'object_': 'nereid.user,%d' % new_nereid_user.id,
            }])

            with app.test_client() as c:
                # Login success
                rv = c.post('/login', data=login_data)
                self.assertEqual(rv.location, 'http://localhost/?locale=en_US')
                self.assertEqual(rv.status_code, 302)

                # Stream Length Count
                rv = c.get('/user/activity-stream')
                rv_json = json.loads(rv.data)
                self.assertEqual(rv_json['totalItems'], 4)

            self.NereidUser.delete([new_nereid_user])

            with app.test_client() as c:
                # Login success
                rv = c.post('/login', data=login_data)
                self.assertEqual(rv.location, 'http://localhost/?locale=en_US')
                self.assertEqual(rv.status_code, 302)

                # Stream Length Count
                rv = c.get('/user/activity-stream')
                rv_json = json.loads(rv.data)
                self.assertEqual(rv_json['totalItems'], 3)

    def test0030_public_stream(self):
        '''
        Checks public stream
        '''
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            user_model, = self.Model.search([
                ('model', '=', 'nereid.user')
            ])

            self.ActivityAllowedModel.create([{
                'name': 'User',
                'model': user_model.id,
            }])

            # Create Activities
            self.Activity.create([{
                'verb': 'Added a new friend',
                'actor': self.registered_user,
                'object_': 'nereid.user,%s' % self.user_party.id,
            }])

            self.Activity.create([{
                'verb': 'Added a friend to a list',
                'actor': self.registered_user,
                'object_': 'nereid.user,%s' % self.user_party.id,
                'target': 'nereid.user,%s' % self.user_party.id,
            }])

            with app.test_client() as c:
                # Get public activity stream
                rv = c.get('/activity-stream')
                rv_json = json.loads(rv.data)

                # No activity stream available publicly
                self.assertEqual(rv_json['totalItems'], 0)


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

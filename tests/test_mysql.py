# encoding: utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

from unittest import TestCase

from mo_parsing.debug import Debugger

from mo_sql_parsing import parse_mysql


class TestMySql(TestCase):
    def test_issue_22(self):
        sql = 'SELECT "fred"'
        result = parse_mysql(sql)
        expected = {"select": {"value": {"literal": "fred"}}}
        self.assertEqual(result, expected)

    def test_issue_126(self):
        from mo_sql_parsing import parse_mysql as parse

        result = parse(
            """SELECT algid, item_id, avg(score) as avg_score 
            from (
                select 
                    ds, 
                    algid, 
                    uin, 
                    split(item_result, ":")[0] as item_id, 
                    split(item_result, ": ")[1] as score 
                from (
                    select ds, scorealgid_ as algid, uin_ as uin, item_result 
                    from (
                        select * 
                        from t_dwd_tmp_wxpay_discount_model_score_hour 
                        where ds >= 2022080300 and ds <= 2022080323
                    )day_tbl 
                    LATERAL VIEW explode(split(scoreresult_, "\\ | ")) temp AS item_result
                ) t
            ) tbl 
            group by algid, item_id;"""
        )
        expected = {
            "from": {
                "name": "tbl",
                "value": {
                    "from": {
                        "name": "t",
                        "value": {
                            "from": [
                                {
                                    "name": "day_tbl",
                                    "value": {
                                        "from": (
                                            "t_dwd_tmp_wxpay_discount_model_score_hour"
                                        ),
                                        "select": "*",
                                        "where": {"and": [
                                            {"gte": ["ds", 2022080300]},
                                            {"lte": ["ds", 2022080323]},
                                        ]},
                                    },
                                },
                                {"lateral view": {
                                    "name": {"temp": "item_result"},
                                    "value": {"explode": {"split": [
                                        "scoreresult_",
                                        {"literal": "\\ | "},
                                    ]}},
                                }},
                            ],
                            "select": [
                                {"value": "ds"},
                                {"name": "algid", "value": "scorealgid_"},
                                {"name": "uin", "value": "uin_"},
                                {"value": "item_result"},
                            ],
                        },
                    },
                    "select": [
                        {"value": "ds"},
                        {"value": "algid"},
                        {"value": "uin"},
                        {
                            "name": "item_id",
                            "value": {"get": [
                                {"split": ["item_result", {"literal": ":"}]},
                                0,
                            ]},
                        },
                        {
                            "name": "score",
                            "value": {"get": [
                                {"split": ["item_result", {"literal": ": "}]},
                                1,
                            ]},
                        },
                    ],
                },
            },
            "groupby": [{"value": "algid"}, {"value": "item_id"}],
            "select": [
                {"value": "algid"},
                {"value": "item_id"},
                {"name": "avg_score", "value": {"avg": "score"}},
            ],
        }
        self.assertEqual(result, expected)

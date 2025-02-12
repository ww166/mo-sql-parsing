# encoding: utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

from unittest import TestCase, skip

from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_sql_parsing import parse_bigquery as parse


class TestBigQuery(TestCase):
    def test_with_expression(self):
        # https://github.com/pyparsing/pyparsing/issues/291
        sql = (
            'with t as (CASE EXTRACT(dayofweek FROM CURRENT_DATETIME()) when 1 then "S"'
            " end) select * from t"
        )
        result = parse(sql)
        expected = {
            "from": "t",
            "select": "*",
            "with": {
                "name": "t",
                "value": {"case": {
                    "then": {"literal": "S"},
                    "when": {"eq": [{"extract": ["dow", {"current_datetime": {}}]}, 1]},
                }},
            },
        }
        self.assertEqual(result, expected)

    def testA(self):
        sql = """SELECT FIRST_VALUE(finish_time) OVER w1 AS fastest_time"""
        result = parse(sql)
        expected = {"select": {
            "name": "fastest_time",
            "over": "w1",
            "value": {"first_value": "finish_time"},
        }}
        self.assertEqual(result, expected)

    def testB(self):
        sql = """
          SELECT 
            name,
            FIRST_VALUE(finish_time) OVER w1 AS fastest_time,
            NTH_VALUE(finish_time, 2) OVER w1 as second_fastest
          FROM finishers
          WINDOW w1 AS (
            PARTITION BY division ORDER BY finish_time ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
          )
        """
        result = parse(sql)
        expected = {
            "from": [
                "finishers",
                {"window": {
                    "name": "w1",
                    "value": {
                        "orderby": {"sort": "asc", "value": "finish_time"},
                        "partitionby": "division",
                        "range": {},
                    },
                }},
            ],
            "select": [
                {"value": "name"},
                {
                    "name": "fastest_time",
                    "over": "w1",
                    "value": {"first_value": "finish_time"},
                },
                {
                    "name": "second_fastest",
                    "over": "w1",
                    "value": {"nth_value": ["finish_time", 2]},
                },
            ],
        }
        self.assertEqual(result, expected)

    def testF(self):
        sql = """
            SELECT
              PERCENTILE_CONT(x, 0) OVER() AS min,
              PERCENTILE_CONT(x, 0.01) OVER() AS percentile1,
              PERCENTILE_CONT(x, 0.5) OVER() AS median,
              PERCENTILE_CONT(x, 0.9) OVER() AS percentile90,
              PERCENTILE_CONT(x, 1) OVER() AS max
            FROM UNNEST([0, 3, NULL, 1, 2]) AS x LIMIT 1
            """
        result = parse(sql)
        expected = {
            "from": {
                "name": "x",
                "value": {"unnest": {"create_array": [0, 3, {"null": {}}, 1, 2]}},
            },
            "limit": 1,
            "select": [
                {"name": "min", "over": {}, "value": {"percentile_cont": ["x", 0]}},
                {
                    "name": "percentile1",
                    "over": {},
                    "value": {"percentile_cont": ["x", 0.01]},
                },
                {
                    "name": "median",
                    "over": {},
                    "value": {"percentile_cont": ["x", 0.5]},
                },
                {
                    "name": "percentile90",
                    "over": {},
                    "value": {"percentile_cont": ["x", 0.9]},
                },
                {"name": "max", "over": {}, "value": {"percentile_cont": ["x", 1]}},
            ],
        }
        self.assertEqual(result, expected)

    def testG(self):
        sql = """
               SELECT
                 x,
                 PERCENTILE_DISC(x, 0) OVER() AS min,
                 PERCENTILE_DISC(x, 0.5) OVER() AS median,
                 PERCENTILE_DISC(x, 1) OVER() AS max
               FROM UNNEST(['c', NULL, 'b', 'a']) AS x
               """
        result = parse(sql)
        expected = {
            "from": {
                "name": "x",
                "value": {"unnest": {"create_array": [
                    {"literal": "c"},
                    {"null": {}},
                    {"literal": "b"},
                    {"literal": "a"},
                ]}},
            },
            "select": [
                {"value": "x"},
                {"name": "min", "over": {}, "value": {"percentile_disc": ["x", 0]}},
                {
                    "name": "median",
                    "over": {},
                    "value": {"percentile_disc": ["x", 0.5]},
                },
                {"name": "max", "over": {}, "value": {"percentile_disc": ["x", 1]}},
            ],
        }

        self.assertEqual(result, expected)

    def testL(self):
        sql = """SELECT PERCENTILE_DISC(x, 0) OVER() AS min"""
        result = parse(sql)
        expected = {"select": {
            "name": "min",
            "value": {"percentile_disc": ["x", 0]},
            "over": {},
        }}
        self.assertEqual(result, expected)

    def testI(self):
        sql = """
            WITH date_hour_slots AS (
             SELECT
                [
                    STRUCT(
                        " 00:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01', current_date(), INTERVAL 1 DAY) as dt_range
                    ),
                    STRUCT(
                        " 01:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range
                    )
                ] AS full_timestamps
            )
            SELECT
                dt AS dates, 
                hrs, 
                CAST(CONCAT( CAST(dt as STRING), CAST(hrs as STRING)) as TIMESTAMP) as timestamp_value
            FROM 
                `date_hour_slots`, 
                date_hour_slots.full_timestamps 
            LEFT JOIN 
                full_timestamps.dt_range as dt
            """
        result = parse(sql)
        expected = {
            "from": [
                "date_hour_slots",
                "date_hour_slots.full_timestamps",
                {"left join": {"name": "dt", "value": "full_timestamps.dt_range"}},
            ],
            "select": [
                {"name": "dates", "value": "dt"},
                {"value": "hrs"},
                {
                    "name": "timestamp_value",
                    "value": {"cast": [
                        {"concat": [
                            {"cast": ["dt", {"string": {}}]},
                            {"cast": ["hrs", {"string": {}}]},
                        ]},
                        {"timestamp": {}},
                    ]},
                },
            ],
            "with": {
                "name": "date_hour_slots",
                "value": {"select": {
                    "name": "full_timestamps",
                    "value": {"create_array": [
                        {"create_struct": [
                            {"name": "hrs", "value": {"literal": " 00:00:00 UTC"}},
                            {
                                "name": "dt_range",
                                "value": {"generate_date_array": [
                                    {"literal": "2016-01-01"},
                                    {"current_date": {}},
                                    {"interval": [1, "day"]},
                                ]},
                            },
                        ]},
                        {"create_struct": [
                            {"name": "hrs", "value": {"literal": " 01:00:00 UTC"}},
                            {
                                "name": "dt_range",
                                "value": {"generate_date_array": [
                                    {"literal": "2016-01-01"},
                                    {"current_date": {}},
                                    {"interval": [1, "day"]},
                                ]},
                            },
                        ]},
                    ]},
                }},
            },
        }
        self.assertEqual(result, expected)

    def testH(self):
        sql = """
            SELECT
                -- [foo],
                ARRAY[foo],
                -- ARRAY<int64, STRING>[foo, bar],  INVALID
                ARRAY<STRING>[foo, bar],
                STRUCT(1, 3),
                STRUCT<int64, STRING>(2, 'foo')
            FROM
                T
            """
        result = parse(sql)
        expected = {
            "from": "T",
            "select": [
                {"value": {"create_array": "foo"}},
                {"value": {"cast": [
                    {"create_array": ["foo", "bar"]},
                    {"array": {"string": {}}},
                ]}},
                {"value": {"create_struct": [1, 3]}},
                {"value": {"cast": [
                    {"create_struct": [2, {"literal": "foo"}]},
                    {"struct": [{"int64": {}}, {"string": {}}]},
                ]}},
            ],
        }

        self.assertEqual(result, expected)

    def testK(self):
        sql = """
            SELECT
                STRUCT<int64, STRING>(2, 'foo')
            """
        result = parse(sql)
        expected = {"select": {"value": {"cast": [
            {"create_struct": [2, {"literal": "foo"}]},
            {"struct": [{"int64": {}}, {"string": {}}]},
        ]}}}

        self.assertEqual(result, expected)

    def testJ(self):
        sql = """
            SELECT
                current_date(),
                GENERATE_ARRAY(5, NULL, 1),
                GENERATE_DATE_ARRAY('2016-10-05', '2016-10-01', INTERVAL 1 DAY),
                GENERATE_DATE_ARRAY('2016-10-05', NULL),
                GENERATE_DATE_ARRAY('2016-01-01', '2016-12-31', INTERVAL 2 MONTH),
                GENERATE_DATE_ARRAY('2000-02-01',current_date(), INTERVAL 1 DAY),
                GENERATE_TIMESTAMP_ARRAY('2016-10-05 00:00:00', '2016-10-05 00:00:02', INTERVAL 1 SECOND)
            FROM
                bar
            """
        result = parse(sql)
        expected = {
            "from": "bar",
            "select": [
                {"value": {"current_date": {}}},
                {"value": {"generate_array": [5, {"null": {}}, 1]}},
                {"value": {"generate_date_array": [
                    {"literal": "2016-10-05"},
                    {"literal": "2016-10-01"},
                    {"interval": [1, "day"]},
                ]}},
                {"value": {"generate_date_array": [
                    {"literal": "2016-10-05"},
                    {"null": {}},
                ]}},
                {"value": {"generate_date_array": [
                    {"literal": "2016-01-01"},
                    {"literal": "2016-12-31"},
                    {"interval": [2, "month"]},
                ]}},
                {"value": {"generate_date_array": [
                    {"literal": "2000-02-01"},
                    {"current_date": {}},
                    {"interval": [1, "day"]},
                ]}},
                {"value": {"generate_timestamp_array": [
                    {"literal": "2016-10-05 00:00:00"},
                    {"literal": "2016-10-05 00:00:02"},
                    {"interval": [1, "second"]},
                ]}},
            ],
        }
        self.assertEqual(result, expected)

    def testN(self):
        sql = """
            SELECT DATE_SUB(current_date("-08:00"), INTERVAL 2 DAY)
            """
        result = parse(sql)
        expected = {"select": {"value": {"date_sub": [
            {"current_date": {"literal": "-08:00"}},
            {"interval": [2, "day"]},
        ]}}}
        self.assertEqual(result, expected)

    def testQ(self):
        sql = """
            WITH a AS (
                SELECT b FROM c
                UNION ALL
                (
                    WITH d AS (
                        SELECT e FROM f
                    )
                    SELECT g FROM d
                )
            )
            SELECT h FROM a
            """
        result = parse(sql)
        expected = {
            "from": "a",
            "select": {"value": "h"},
            "with": {
                "name": "a",
                "value": {"union_all": [
                    {"from": "c", "select": {"value": "b"}},
                    {
                        "from": "d",
                        "select": {"value": "g"},
                        "with": {
                            "name": "d",
                            "value": {"from": "f", "select": {"value": "e"}},
                        },
                    },
                ]},
            },
        }
        self.assertEqual(result, expected)

    def testU(self):
        sql = """SELECT  * FROM `a`.b.`c`"""
        result = parse(sql)
        expected = {"from": "a.b.c", "select": "*"}
        self.assertEqual(result, expected)

    def testV(self):
        sql = """SELECT * FROM `a.b.c` a1
                JOIN `a.b.d` a2
                    ON cast(a1.field AS BIGDECIMAL) = cast(a2.field AS BIGNUMERIC)"""
        result = parse(sql)
        expected = {
            "select": "*",
            "from": [
                {"value": "a..b..c", "name": "a1"},
                {
                    "join": {"value": "a..b..d", "name": "a2"},
                    "on": {"eq": [
                        {"cast": ["a1.field", {"bigdecimal": {}}]},
                        {"cast": ["a2.field", {"bignumeric": {}}]},
                    ]},
                },
            ],
        }
        self.assertEqual(result, expected)

    def testW(self):
        sql = """SELECT * FROM `a.b.c` a1
                JOIN `a.b.d` a2
                    ON cast(a1.field AS INT64) = cast(a2.field AS BYTEINT)"""
        result = parse(sql)
        expected = {
            "select": "*",
            "from": [
                {"value": "a..b..c", "name": "a1"},
                {
                    "join": {"value": "a..b..d", "name": "a2"},
                    "on": {"eq": [
                        {"cast": ["a1.field", {"int64": {}}]},
                        {"cast": ["a2.field", {"byteint": {}}]},
                    ]},
                },
            ],
        }
        self.assertEqual(result, expected)

    def testS(self):
        sql = """
            SELECT * FROM 'a'.b.`c`
            """
        with FuzzyTestCase.assertRaises(
            """'a'.b.`c`" (at char 27), (line:2, col:27)"""
        ):
            parse(sql)

    def test_issue_96_r_expressions1(self):
        result = parse("SELECT regex_extract(x, r'[a-z]'), value FROM `a.b.c`")
        expected = {
            "from": "a..b..c",
            "select": [
                {"value": {"regex_extract": ["x", {"regex": "[a-z]"}]}},
                {"value": "value"},
            ],
        }
        self.assertEqual(result, expected)

    def test_issue_96_r_expressions2(self):
        result = parse('SELECT regex_extract(x, r"[a-z]"), value FROM `a.b.c`')
        expected = {
            "from": "a..b..c",
            "select": [
                {"value": {"regex_extract": ["x", {"regex": "[a-z]"}]}},
                {"value": "value"},
            ],
        }
        self.assertEqual(result, expected)

    def test_issue_97_safe_cast(self):
        result = parse("SELECT SAFE_CAST(x AS STRING) from `a.b.c`")
        expected = {
            "from": "a..b..c",
            "select": {"value": {"safe_cast": ["x", {"string": {}}]}},
        }
        self.assertEqual(result, expected)

    def test_issue_98_interval1(self):
        result = parse(
            """SELECT timestamp_add('2022-07-14T12:42:11Z', INTERVAL x MINUTE)"""
        )
        expected = {"select": {"value": {"timestamp_add": [
            {"literal": "2022-07-14T12:42:11Z"},
            {"interval": ["x", "minute"]},
        ]}}}
        self.assertEqual(result, expected)

    @skip("missing FROM?")
    def test_issue_98_interval2(self):
        result = parse(
            """SELECT timestamp_add('2022-07-14T12:42:11Z', INTERVAL x MINUTE) UNNEST(GENERATE_ARRAY(1, 10)) as x"""
        )
        expected = {}
        self.assertEqual(result, expected)

    def test_issue_99_select_except(self):
        result = parse("SELECT * EXCEPT(x) FROM `a.b.c`")
        expected = {"from": "a..b..c", "select_except": {"value": "x"}}
        self.assertEqual(result, expected)

    def test_unnest(self):
        result = parse(
            """SELECT * FROM UNNEST([1, 2, 2, 5, NULL]) AS unnest_column WITH OFFSET AS `offset`"""
        )
        expected = {
            "select": "*",
            "from": {
                "name": "unnest_column",
                "value": {"unnest": {"create_array": [1, 2, 2, 5, {"null": {}}]}},
                "with_offset": "offset",
            },
        }
        self.assertEqual(result, expected)

    def test_issue_123_declare1(self):
        sql = """DECLARE _current_timestamp timestamp DEFAULT current_timestamp();"""
        result = parse(sql)
        expected = {"declare": {
            "name": "_current_timestamp",
            "type": {"timestamp": {}},
            "default": {"current_timestamp": {}},
        }}
        self.assertEqual(result, expected)

    def test_issue_123_declare2(self):
        sql = """DECLARE _current_date      date      DEFAULT current_date("America/Sao_Paulo");"""
        result = parse(sql)
        expected = {"declare": {
            "name": "_current_date",
            "type": {"date": {}},
            "default": {"current_date": {"literal": "America/Sao_Paulo"}},
        }}
        self.assertEqual(result, expected)

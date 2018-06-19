from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import super
import unittest
from parameterized import parameterized
from datetime import datetime, timedelta
import pytz
import time
from pprint import pprint
from beem import Steem
from beem.blockchain import Blockchain
from beem.block import Block
from beem.instance import set_shared_steem_instance
from beem.nodelist import NodeList


class Testcases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        nodelist = NodeList()
        nodelist.update_nodes(steem_instance=Steem(node=nodelist.get_nodes(normal=True, appbase=True), num_retries=10))
        cls.bts = Steem(
            node=nodelist.get_nodes(),
            nobroadcast=True,
            timeout=30,
            num_retries=30,
        )
        # from getpass import getpass
        # self.bts.wallet.unlock(getpass())
        set_shared_steem_instance(cls.bts)
        cls.bts.set_default_account("test")

        b = Blockchain(steem_instance=cls.bts)
        num = b.get_current_block_num()
        # num = 23346630
        cls.start = num - 50
        cls.stop = num
        # cls.N_transfer = 121
        # cls.N_vote = 2825

    def test_stream_threading(self):
        bts = self.bts
        b = Blockchain(steem_instance=bts)
        ops_stream = []
        ops_stream_no_threading = []
        opNames = ["transfer", "vote"]
        block_num_list = []
        for op in b.stream(opNames=opNames, start=self.start, stop=self.stop, threading=True, thread_num=8):
            ops_stream.append(op)
            if op["block_num"] not in block_num_list:
                block_num_list.append(op["block_num"])
        block_num_list2 = []
        for op in b.stream(opNames=opNames, start=self.start, stop=self.stop, threading=False):
            ops_stream_no_threading.append(op)
            if op["block_num"] not in block_num_list2:
                block_num_list2.append(op["block_num"])

        self.assertEqual(ops_stream[0]["block_num"], ops_stream_no_threading[0]["block_num"])
        self.assertEqual(ops_stream[-1]["block_num"], ops_stream_no_threading[-1]["block_num"])

        self.assertEqual(len(block_num_list), len(block_num_list2))
        for i in range(len(block_num_list)):
            self.assertEqual(block_num_list[i], block_num_list2[i])

        ops_blocks = []
        last_id = self.start - 1
        for op in b.blocks(start=self.start, stop=self.stop, threading=True, thread_num=8):
            ops_blocks.append(op)
            self.assertEqual(op.identifier, last_id + 1)
            last_id += 1
        self.assertEqual(len(ops_stream_no_threading), len(ops_stream))
        for i in range(len(ops_blocks)):
            self.assertEqual(ops_blocks[i]["id"], block_num_list2[i])

        op_stat4 = {"transfer": 0, "vote": 0}
        self.assertTrue(len(ops_blocks) > 0)
        for block in ops_blocks:
            for op in block.operations:
                op_type = ""
                if isinstance(op, dict) and 'type' in op:
                    op_type = op["type"]
                    if len(op_type) > 10 and op_type[len(op_type) - 10:] == "_operation":
                        op_type = op_type[:-10]
                else:
                    if "op" in op:
                        op_type = op["op"][0]
                    else:
                        op_type = op[0]
                if op_type in opNames:
                    op_stat4[op_type] += 1
            self.assertTrue(block.identifier >= self.start)
            self.assertTrue(block.identifier <= self.stop)
        self.assertEqual(len(ops_stream_no_threading), op_stat4["transfer"] + op_stat4["vote"])

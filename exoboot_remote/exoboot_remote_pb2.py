# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: exoboot_remote.proto
# Protobuf Python Version: 5.26.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x14\x65xoboot_remote.proto\"\x06\n\x04null\"\x1b\n\x07receipt\x12\x10\n\x08received\x18\x01 \x01(\x08\"\x17\n\x05pause\x12\x0e\n\x06mybool\x18\x01 \x01(\x08\"\x15\n\x03log\x12\x0e\n\x06mybool\x18\x01 \x01(\x08\"\x16\n\x04quit\x12\x0e\n\x06mybool\x18\x01 \x01(\x08\">\n\x07torques\x12\x18\n\x10peak_torque_left\x18\x01 \x01(\x02\x12\x19\n\x11peak_torque_right\x18\x02 \x01(\x02\"\x08\n\x06\x62\x65\x61ver\"\x16\n\x07testmsg\x12\x0b\n\x03msg\x18\x01 \x01(\t\"\x85\x01\n\x0csubject_info\x12\x12\n\nstartstamp\x18\x01 \x01(\x02\x12\x11\n\tsubjectID\x18\x02 \x01(\t\x12\x12\n\ntrial_type\x18\x03 \x01(\t\x12\x12\n\ntrial_cond\x18\x04 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x05 \x01(\t\x12\x11\n\tusebackup\x18\x06 \x01(\x08\"o\n\x06result\x12\t\n\x01t\x18\x01 \x01(\x02\x12\x13\n\x0bsubject_bid\x18\x02 \x01(\x02\x12\x15\n\ruser_win_flag\x18\x03 \x01(\x08\x12\x16\n\x0e\x63urrent_payout\x18\x04 \x01(\x02\x12\x16\n\x0etotal_winnings\x18\x05 \x01(\x02\"3\n\x06survey\x12\t\n\x01t\x18\x01 \x01(\x02\x12\x11\n\tenjoyment\x18\x02 \x01(\x02\x12\x0b\n\x03rpe\x18\x03 \x01(\x02\"\x14\n\x07walkmsg\x12\t\n\x01t\x18\x01 \x01(\x02\"8\n\x08vas_info\x12\x0f\n\x07\x62tn_num\x18\x01 \x01(\x02\x12\r\n\x05trial\x18\x02 \x01(\x02\x12\x0c\n\x04pres\x18\x03 \x01(\x02\"6\n\x06slider\x12\x0e\n\x06pitime\x18\x01 \x01(\x02\x12\x0f\n\x07torques\x18\x02 \x03(\x02\x12\x0b\n\x03mvs\x18\x03 \x03(\x02\"`\n\x0cpresentation\x12\x12\n\nbtn_option\x18\x01 \x01(\x02\x12\r\n\x05trial\x18\x02 \x01(\x02\x12\x0c\n\x04pres\x18\x03 \x01(\x02\x12\x0f\n\x07torques\x18\x04 \x03(\x02\x12\x0e\n\x06values\x18\x05 \x03(\x02\"t\n\ncomparison\x12\x0c\n\x04walk\x18\x01 \x01(\x02\x12\x0c\n\x04pres\x18\x02 \x01(\x02\x12\x0c\n\x04prop\x18\x03 \x01(\x02\x12\r\n\x05T_ref\x18\x04 \x01(\x02\x12\x0e\n\x06T_comp\x18\x05 \x01(\x02\x12\r\n\x05truth\x18\x06 \x01(\x02\x12\x0e\n\x06\x61nswer\x18\x07 \x01(\x02\"\x1a\n\nwalkmsgjnd\x12\x0c\n\x04walk\x18\x01 \x01(\x02\"*\n\npreference\x12\x0c\n\x04pres\x18\x01 \x01(\x02\x12\x0e\n\x06torque\x18\x02 \x01(\x02\"\x17\n\x06header\x12\r\n\x05names\x18\x01 \x03(\t\"\x15\n\x04type\x12\r\n\x05types\x18\x01 \x03(\t\"\x1a\n\ndatastream\x12\x0c\n\x04\x64\x61ta\x18\x01 \x03(\t2\x86\x05\n\x14\x65xoboot_over_network\x12&\n\x0etestconnection\x12\x08.testmsg\x1a\x08.receipt\"\x00\x12(\n\x10get_subject_info\x12\x05.null\x1a\r.subject_info\x12\x1b\n\x04\x63hop\x12\x07.beaver\x1a\x08.receipt\"\x00\x12\x1f\n\tset_pause\x12\x06.pause\x1a\x08.receipt\"\x00\x12\x1d\n\x08set_quit\x12\x05.quit\x1a\x08.receipt\"\x00\x12\x1b\n\x07set_log\x12\x04.log\x1a\x08.receipt\"\x00\x12\"\n\nset_torque\x12\x08.torques\x1a\x08.receipt\"\x00\x12\x1b\n\x04\x63\x61ll\x12\x07.result\x1a\x08.receipt\"\x00\x12\x1f\n\x08question\x12\x07.survey\x1a\x08.receipt\"\x00\x12\x1f\n\x07newwalk\x12\x08.walkmsg\x1a\x08.receipt\"\x00\x12(\n\x0fupdate_vas_info\x12\t.vas_info\x1a\x08.receipt\"\x00\x12$\n\rslider_update\x12\x07.slider\x1a\x08.receipt\"\x00\x12\x30\n\x13presentation_result\x12\r.presentation\x1a\x08.receipt\"\x00\x12 \n\x07newpres\x12\t.vas_info\x1a\x08.receipt\"\x00\x12,\n\x11\x63omparison_result\x12\x0b.comparison\x1a\x08.receipt\"\x00\x12%\n\nnewwalkjnd\x12\x0b.walkmsgjnd\x1a\x08.receipt\"\x00\x12&\n\x0bpref_result\x12\x0b.preference\x1a\x08.receipt\"\x00\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'exoboot_remote_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_NULL']._serialized_start=24
  _globals['_NULL']._serialized_end=30
  _globals['_RECEIPT']._serialized_start=32
  _globals['_RECEIPT']._serialized_end=59
  _globals['_PAUSE']._serialized_start=61
  _globals['_PAUSE']._serialized_end=84
  _globals['_LOG']._serialized_start=86
  _globals['_LOG']._serialized_end=107
  _globals['_QUIT']._serialized_start=109
  _globals['_QUIT']._serialized_end=131
  _globals['_TORQUES']._serialized_start=133
  _globals['_TORQUES']._serialized_end=195
  _globals['_BEAVER']._serialized_start=197
  _globals['_BEAVER']._serialized_end=205
  _globals['_TESTMSG']._serialized_start=207
  _globals['_TESTMSG']._serialized_end=229
  _globals['_SUBJECT_INFO']._serialized_start=232
  _globals['_SUBJECT_INFO']._serialized_end=365
  _globals['_RESULT']._serialized_start=367
  _globals['_RESULT']._serialized_end=478
  _globals['_SURVEY']._serialized_start=480
  _globals['_SURVEY']._serialized_end=531
  _globals['_WALKMSG']._serialized_start=533
  _globals['_WALKMSG']._serialized_end=553
  _globals['_VAS_INFO']._serialized_start=555
  _globals['_VAS_INFO']._serialized_end=611
  _globals['_SLIDER']._serialized_start=613
  _globals['_SLIDER']._serialized_end=667
  _globals['_PRESENTATION']._serialized_start=669
  _globals['_PRESENTATION']._serialized_end=765
  _globals['_COMPARISON']._serialized_start=767
  _globals['_COMPARISON']._serialized_end=883
  _globals['_WALKMSGJND']._serialized_start=885
  _globals['_WALKMSGJND']._serialized_end=911
  _globals['_PREFERENCE']._serialized_start=913
  _globals['_PREFERENCE']._serialized_end=955
  _globals['_HEADER']._serialized_start=957
  _globals['_HEADER']._serialized_end=980
  _globals['_TYPE']._serialized_start=982
  _globals['_TYPE']._serialized_end=1003
  _globals['_DATASTREAM']._serialized_start=1005
  _globals['_DATASTREAM']._serialized_end=1031
  _globals['_EXOBOOT_OVER_NETWORK']._serialized_start=1034
  _globals['_EXOBOOT_OVER_NETWORK']._serialized_end=1680
# @@protoc_insertion_point(module_scope)
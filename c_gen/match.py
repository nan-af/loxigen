# Copyright 2013, Big Switch Networks, Inc.
#
# LoxiGen is licensed under the Eclipse Public License, version 1.0 (EPL), with
# the following special exception:
#
# LOXI Exception
#
# As a special exception to the terms of the EPL, you may distribute libraries
# generated by LoxiGen (LoxiGen Libraries) under the terms of your choice, provided
# that copyright and licensing notices generated by LoxiGen are not altered or removed
# from the LoxiGen Libraries and the notice provided below is (i) included in
# the LoxiGen Libraries, if distributed in source code form and (ii) included in any
# documentation for the LoxiGen Libraries, if distributed in binary form.
#
# Notice: "Copyright 2013, Big Switch Networks, Inc. This library was generated by the LoxiGen Compiler."
#
# You may not use this file except in compliance with the EPL or LOXI Exception. You may obtain
# a copy of the EPL at:
#
# http://www.eclipse.org/legal/epl-v10.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# EPL for the specific language governing permissions and limitations
# under the EPL.

# @brief Match data representation
#
# @fixme This still has lots of C specific code that should be moved into c_gen

import sys
import c_gen.of_g_legacy as of_g
from generic_utils import *
import c_gen.loxi_utils_legacy as loxi_utils
import loxi_globals

#
# Use 1.2 match semantics for common case
#
# Generate maps between generic match and version specific matches
# Generate dump functions for generic match
# Generate dump functions for version specific matches

## @var of_match_members
# The dictionary from unified match members to type and indexing info
#
# Keys:
#   name The unified name used for the member
#   m_type The data type used for the object in unified structure
#   order Used to define an order for readability
#   v1_wc_shift The WC shift in OF 1.0
#   v2_wc_shift The WC shift in OF 1.1
#
# We use the 1.2 names and alias older names

of_match_members = dict()

of_v1_keys = [
    "eth_dst",
    "eth_src",
    "eth_type",
    "in_port",
    "ipv4_dst",
    "ip_proto",
    "ipv4_src",
    "ip_dscp",
    "tcp_dst",  # Means UDP too for 1.0 and 1.1
    "tcp_src",  # Means UDP too for 1.0 and 1.1
    "vlan_pcp",
    "vlan_vid"
    ]

v1_wc_shifts = dict(
    in_port=0,
    vlan_vid=1,
    eth_src=2,
    eth_dst=3,
    eth_type=4,
    ip_proto=5,
    tcp_src=6,
    tcp_dst=7,
    ipv4_src=8,
    ipv4_dst=14,
    vlan_pcp=20,
    ip_dscp=21,
)

of_v2_keys = [
    "eth_dst",
    "eth_src",
    "eth_type",
    "in_port",
    "ipv4_dst",
    "ip_proto",
    "ipv4_src",
    "ip_dscp",
    "tcp_dst",  # Means UDP too for 1.0 and 1.1
    "tcp_src",  # Means UDP too for 1.0 and 1.1
    "vlan_pcp",
    "vlan_vid",
    "mpls_label",
    "mpls_tc",
    "metadata"
    ]

of_v2_full_mask = [
    "eth_dst",
    "eth_src",
    "ipv4_dst",
    "ipv4_src",
    "metadata"
    ]

v2_wc_shifts = dict(
    in_port=0,
    vlan_vid=1,
    vlan_pcp=2,
    eth_type=3,
    ip_dscp=4,
    ip_proto=5,
    tcp_src=6,
    tcp_dst=7,
    mpls_label=8,
    mpls_tc=9,
)

# Map from wire version to list of match keys for that version
match_keys = {
    1: of_v1_keys,
    2: of_v2_keys,
    3: [],
    4: [],
}

# Complete list of match keys, sorted by the standard order
match_keys_sorted = []

# Generate the of_match_members, match_keys, and match_keys_sorted
# datastructures from the IR and the v1/v2 tables above
def build():
    count = 0
    for uclass in loxi_globals.unified.classes:
        if not uclass.is_oxm or uclass.name == 'of_oxm':
            continue
        if uclass.name.endswith('_masked'):
            continue

        name = uclass.name[7:] # of_oxm_*
        value_member = uclass.member_by_name('value')
        type_len = uclass.member_by_name('type_len').value

        # Order match keys by their type_len
        if (type_len & 0xffff0000) == 0x80000000:
            # OpenFlow Basic comes first
            order = type_len & 0x0000ffff
        else:
            order = type_len

        match_member = dict(
            name=name,
            m_type=value_member.oftype,
            order=order)
        if name in v1_wc_shifts:
            match_member['v1_wc_shift'] = v1_wc_shifts[name]
        if name in v2_wc_shifts:
            match_member['v2_wc_shift'] = v2_wc_shifts[name]

        of_match_members[name] = match_member

        for version in uclass.version_classes:
            match_keys[version.wire_version].append(name)

    match_keys_sorted.extend(of_match_members.keys())
    match_keys_sorted.sort(key=lambda entry:of_match_members[entry]["order"])

##
# Check that all members in the hash are recognized as match keys
def match_sanity_check():
    count = 0
    for match_v in ["of_match_v1", "of_match_v2"]:
        count += 1
        for mm in of_g.unified[match_v][count]["members"]:
            key = mm["name"]
            if key.find("_mask") >= 0:
                continue
            if loxi_utils.skip_member_name(key):
                continue
            if key == "wildcards":
                continue
            if not key in of_match_members:
                print "Key %s not found in match struct, v %s" % (key, match_v)
                sys.exit(1)

    # Generate list of OXM names from the unified classes
    oxm_names = [x[7:] for x in of_g.unified.keys() if
                 x.startswith('of_oxm_') and
                 x.find('masked') < 0 and
                 x.find('header') < 0]

    # Check that all OXMs are in the match members
    for key in oxm_names:
        if not key in of_match_members:
            if not (key.find("_masked") > 0):
                debug("Key %s in OXM, not of_match_members" % key)
                sys.exit(1)
            if not key[:-7] in of_match_members:
                debug("Key %s in OXM, but %s not in of_match_members"
                      % (key, key[:-7]))
                sys.exit(1)

    # Check that all match members are in the OXMs
    for key in of_match_members:
        if not key in oxm_names:
            debug("Key %s in of_match_members, not in OXM" % key)
            sys.exit(1)
        oxm_type = of_g.unified['of_oxm_%s' % key]['union']['value']['m_type']
        if of_match_members[key]["m_type"] != oxm_type:
            debug("Type mismatch for key %s in oxm data: %s vs %s" %
                  (key, of_match_members[key]["m_type"], oxm_type))
            sys.exit(1)

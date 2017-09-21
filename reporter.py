#!/usr/bin/python
# -*- coding: utf-8 -*-

# Reporting tool for querying Sales- and Financial Reports from iTunes Connect
#
# This script mimics the official iTunes Connect Reporter by Apple which is used
# to automatically retrieve Sales- and Financial Reports for your App Store sales.
# It is written in pure Python and doesn’t need a Java runtime installation.
# Opposed to Apple’s tool, it can fetch iTunes Connect login credentials from the
# macOS Keychain in order to tighten security a bit. Also, it goes the extra mile
# and unzips the downloaded reports if possible.
#
# Copyright (c) 2016 fedoco <fedoco@users.noreply.github.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import argparse
import json
import zlib
import datetime

import os
import urllib.request
import urllib.error
import urllib.parse

VERSION = '2.2'
ENDPOINT_SALES = 'https://reportingitc-reporter.apple.com/reportservice/sales/v1'
ENDPOINT_FINANCE = 'https://reportingitc-reporter.apple.com/reportservice/finance/v1'


def itc_get_vendors(args):
    command = 'Sales.getVendors'
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))


def itc_get_status(args):
    command = args.service + '.getStatus'
    endpoint = ENDPOINT_SALES if args.service == 'Sales' else ENDPOINT_FINANCE
    output_result(post_request(endpoint, get_credentials(args), command))


def itc_get_accounts(args):
    command = args.service + '.getAccounts'
    endpoint = ENDPOINT_SALES if args.service == 'Sales' else ENDPOINT_FINANCE
    output_result(post_request(endpoint, get_credentials(args), command))


def itc_get_vendor_and_regions(args):
    command = 'Finance.getVendorsAndRegions'
    output_result(post_request(ENDPOINT_FINANCE, get_credentials(args), command))


def itc_get_sales_report(args):
    command = 'Sales.getReport, {0},Sales,Summary,{1},{2}'.format(args.vendor, args.datetype, args.date)
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))


def itc_view_token(args):
    command = 'Sales.viewToken'
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))


def itc_generate_token(args):
    command = 'Sales.generateToken'

    # Generating a new token requires mirroring back a request id to the iTC server. Get service request ID...
    _, header = post_request(ENDPOINT_SALES, get_credentials(args), command)
    service_request_id = header.dict['service_request_id']

    # ...and post back the request id
    result = post_request(
        ENDPOINT_SALES,
        get_credentials(args),
        command, "&isExistingToken=Y&requestId=" + service_request_id)
    output_result(result)


def itc_delete_token(args):
    command = 'Sales.deleteToken'
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))


def get_credentials(args):
    """Select iTunes Connect login credentials depending on given command line arguments"""

    # Most commands require an access token fetched either from the command line or from env
    access_token = args.access_token if args.access_token else os.getenv('ITC_ACCESS_TOKEN', '')

    if not access_token:
        # ...but commands for access token manipulation need the plaintext password of the iTunes Connect account
        password = args.password if args.password else input('iTunes Connect password')
    else:
        password = ''

    return args.userid, access_token, password, str(args.account), args.mode


def build_json_request_string(credentials, query):
    """Build a JSON string from the urlquoted credentials and the actual query input"""

    userid, access_token, password, account, mode = credentials

    request = dict(userid=userid, version=VERSION, mode=mode, queryInput=query)
    if account:
        request.update(account=account)  # empty account info would result in error 404
    if access_token:
        request.update(accesstoken=access_token)
    if password:
        request.update(password=password)

    return urllib.parse.urlencode(dict(jsonRequest=json.dumps(request))).encode('utf-8')


def post_request(endpoint, credentials, command, url_params=None):
    """Execute the HTTP POST request"""

    command = "[p=Reporter.properties, %s]" % command
    request_data = build_json_request_string(credentials, command)
    if url_params:
        request_data += url_params

    request = urllib.request.Request(endpoint, request_data)
    request.add_header('Accept', '*')

    try:
        response = urllib.request.urlopen(request)
        content = response.read()
        header = response.info()

        return content, header

    except urllib.error.HTTPError as e:
        if e.code == 400 or e.code == 401 or e.code == 403 or e.code == 404:
            # for these error codes, the body always contains an error message
            raise ValueError(e.read().decode('utf-8'))
        else:
            raise ValueError("HTTP Error %s. Did you choose reasonable query arguments?" % str(e.code))


def output_result(result, unzip=True):
    """Output (and when necessary unzip) the result of the request to the screen or into a report file"""

    content, header = result

    # Unpack content into the final report file if it is gzip compressed.
    if header.get_content_type() == 'application/a-gzip':
        msg = header.get('downloadmsg')
        filename = header.get('filename') or 'report.txt.gz'
        if unzip:
            msg = msg.replace('.txt.gz', '.txt')
            filename = filename[:-3]
            content = zlib.decompress(content, 15 + 32)

        # TODO: Check if report data already exists f.ex S_M_vendorid_month (Sales_Monthly_VendorID_Month)
        # And use a cache
        # Else format as csv
        with open(filename, 'wb') as file:
            file.write(content)
        print(msg)
    else:
        print(content.decode('utf-8'))


def parse_arguments():
    """Build and parse the command line arguments"""

    parser = argparse.ArgumentParser(
        description="Reporting tool for querying Sales- and Financial Reports from iTunes Connect", epilog="For a detailed description of report types, see http://help.apple.com/itc/appssalesandtrends/#/itc37a18bcbf")

    # (most of the time) optional arguments
    parser.add_argument('-a', '--account', type=int, help="account number (needed if your Apple ID has access to multiple accounts; for a list of your account numbers, use the 'getAccounts' command)")
    parser.add_argument('-m', '--mode', choices=['Normal', 'Robot.XML'], default='Normal', help="output format: plain text or XML (defaults to '%(default)s')")

    # always required arguments
    parser.add_argument('-u', '--userid', required=False, help="Apple ID for use with iTunes Connect")

    # Template for commands that require authentication with password
    parser_auth_password = argparse.ArgumentParser(add_help=False)
    parser_auth_password.set_defaults(access_token=None, access_token_keychain_item=None)
    auth_password_args = parser_auth_password.add_argument_group()
    mutex_group = auth_password_args.add_mutually_exclusive_group(required=True)
    mutex_group.add_argument('-P', '--password', help='Apple ID password (cannot be used together with -p)')

    # Template for commands that require authentication with access token
    parser_auth_token = argparse.ArgumentParser(add_help=False)
    parser_auth_token.set_defaults(password=None, password_keychain_item=None)
    auth_token_args = parser_auth_token.add_argument_group()
    mutex_group = auth_token_args.add_mutually_exclusive_group(required=True)
    mutex_group.add_argument('-T', '--access-token', help='iTunes Connect access token (can be obtained with the generateToken command or via iTunes Connect -> Sales & Trends -> Reports -> About Reports)')

    # Commands
    subparsers = parser.add_subparsers(dest='command', title='commands', description="Specify the task you want to be carried out (use -h after a command's name to get additional help for that command)")

    parser_01 = subparsers.add_parser('getStatus', help="check if iTunes Connect is available for queries", parents=[parser_auth_token])
    parser_01.add_argument('service', choices=['Sales', 'Finance'], default='Sales', help="service endpoint to query")
    parser_01.set_defaults(func=itc_get_status)

    parser_02 = subparsers.add_parser('getAccounts', help="fetch a list of accounts accessible to the Apple ID given in -u", parents=[parser_auth_token])
    parser_02.add_argument('service', choices=['Sales', 'Finance'], default='Sales', help="service endpoint to query")
    parser_02.set_defaults(func=itc_get_accounts)

    parser_03 = subparsers.add_parser('getVendors', help="fetch a list of vendors accessible to the Apple ID given in -u", parents=[parser_auth_token])
    parser_03.set_defaults(func=itc_get_vendors)

    parser_04 = subparsers.add_parser('getVendorsAndRegions', help="fetch a list of financial reports you can download by vendor number and region", parents=[parser_auth_token])
    parser_04.set_defaults(func=itc_get_vendor_and_regions)

    parser_05 = subparsers.add_parser('getSalesReport', help="download a summary sales report file for a specific date range", parents=[parser_auth_token])
    parser_05.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_05.add_argument('datetype', choices=['Daily', 'Weekly', 'Monthly', 'Yearly'], help="length of time covered by the report")
    parser_05.add_argument('date', help="specific time covered by the report (weekly reports use YYYYMMDD, where the day used is the Sunday that week ends; monthly reports use YYYYMM; yearly reports use YYYY)")
    parser_05.set_defaults(func=itc_get_sales_report)

    parser_06 = subparsers.add_parser('generateToken', help="generate a token for accessing iTunes Connect (expires after 180 days)", parents=[parser_auth_password])
    parser_06.set_defaults(func=itc_generate_token)

    parser_07 = subparsers.add_parser('viewToken', help="display current iTunes Connect access token and its expiration date", parents=[parser_auth_password])
    parser_07.set_defaults(func=itc_view_token)

    parser_08 = subparsers.add_parser('deleteToken', help="delete an existing iTunes Connect access token", parents=[parser_auth_password])
    parser_08.set_defaults(func=itc_delete_token)

    args = parser.parse_args()

    try:
        validate_arguments(args)
    except ValueError as e:
        parser.error(e)

    return args


def validate_arguments(args):
    """Do some additional checks on the passed arguments which argparse couldn't handle directly"""

    if not args.account and args.command in ['getVendorsAndRegions', 'getVendors', 'getFinancialReport']:
        raise ValueError("Error: Argument -a/--account is needed for command '%s'" % args.command)

    if hasattr(args, 'fiscalyear'):
        try:
            datetime.datetime.strptime(args.fiscalyear, "%Y")
        except ValueError:
            raise ValueError("Error: Fiscal year must be specified as YYYY")

    if hasattr(args, 'fiscalperiod'):
        try:
            if int(args.fiscalperiod) < 1 or int(args.fiscalperiod) > 12:
                raise Exception
        except ValueError:
            raise ValueError("Error: Fiscal period must be a value between 1 and 12")

    if hasattr(args, 'datetype'):
        date_format = '%Y%m%d'
        error = "Date must be specified as YYYYMMDD for daily reports"
        if args.datetype == 'Weekly':
            error = "Date must be specified as YYYYMMDD for weekly reports. The day used is the Sunday that week ends"
        if args.datetype == 'Monthly':
            error = "Date must be specified as YYYYMM for monthly reports"
            date_format = '%Y%m'
        if args.datetype == 'Yearly':
            error = "Date must be specified as YYYY for yearly reports"
            date_format = '%Y'
        try:
            datetime.datetime.strptime(args.date, date_format)
        except ValueError:
            raise ValueError("Error: " + error)


if __name__ == '__main__':
    main_args = parse_arguments()

    try:
        main_args.func(main_args)
    except ValueError as main_error:
        print(main_error)
        exit(-1)

    exit(0)

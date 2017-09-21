# itc-reporter
Forked from https://github.com/fedoco/itc-reporter with cleanups, python 3 and removed some functionality.

Python replacement for the Apple tool **Reporter**, with no external dependencies.

The argument names and values of this script have mostly been chosen to be consistent with [Apple's documentation for Reporter](https://help.apple.com/itc/appsreporterguide/). To get a quick overview run `./reporter.py -h`:

### Prerequisites

#### Obtaining an iTunes Connect access token
To generate an access token for an Apple ID, log in to iTunes Connect using the Apple ID that you plan to use with `reporter.py`. Go to *Sales and Trends > Reports*, then click on the tooltip next to *About Reports*. Click *Generate Access Token*.

Or, instead of doing these steps manually, you can just let `reporter.py` fetch a token for you from iTunes Connect.

```sh
./reporter.py -u your@apple-id.com generateToken -P YourAppleIDPassword

Your new access token has been generated.
AccessToken:4fbd6016-439d-4cef-a72e-5c465f8343d4
Expiration Date:2018-01-27
```

### Usage examples

#### iTunes Connect's status for sales reports

```sh
./reporter.py getStatus Sales -t "ITC_ACCESS_TOKEN"
```

#### Get accounts

```sh
./reporter.py getAccounts Sales -t "ITC_ACCESS_TOKEN"
```
The result is a list of account numbers you can then specify with the `-a` or `--account` argument in later queries regarding sales reports.

#### Get vendors

```sh
./reporter.py --account 2821955 getVendors -t "ITC_ACCESS_TOKEN"
```

#### Get sales report

The resulting vendor number(s) can then be used to get the actual reports. In the following example, a sales report listing the sales of a single day (2017/07/18) for vendor 85442109 is going to be retrieved:

```sh
./reporter.py -a 2821955 getSalesReport 85442109 Daily 20170718 -t "ITC_ACCESS_TOKEN"
```


## TODO:

- [ ] Cache reports
- [ ] Parse reports
- [ ] JSON output
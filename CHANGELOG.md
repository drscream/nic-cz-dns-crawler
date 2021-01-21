## 1.5.5 (2021-01-21)

Fixed installation issues on MS Windows. See issue #10 for details: https://gitlab.nic.cz/adam/dns-crawler/-/issues/10.

## 1.5.4 (2021-01-19)

Updated most Python deps to latest compatible versions.

### MAIL:

- added GeoIP info for each IP from MX records

## 1.5.3 (2020-10-19)

### MAIL:

- fixed exception handling so more errors occuring when getting banners are recorded
- when there are no MX records, the 2nd level domain name is used as a mail host only if it has at least one A or AAAA record

## 1.5.2 (2020-10-13)

Less confusing error messages (especially for the single-threaded crawler) and GeoIP DB handling. Thanks to Hani Weiss for the [bugreport](https://gitlab.nic.cz/adam/dns-crawler/-/issues/9)!

## 1.5.1 (2020-10-13)

No functionality changes, just updated dependencies – DNSPython from git is no longer needed, installation should be a bit easier now. And it now works even with pip's new resolver (`--use-feature=2020-resolver`).

## 1.5.0 (2020-10-12)

- improvements in communication with Redis, should be more reliable now even with remote hosts 
- added a config option to include a worker name (`<hostname>-<number>`) in the output JSON

### WEB:

- remove unused HTML stripping option (moved to output processing in our pipeline)
- fixed error with extracting the `final_step` when there were no steps in some IPv4/6 80/443 combinations

## 1.4.9 (2020-07-28)

- add a config option to specify custom IPs used for an initial connectivity check and getting a source addresses for HTTP(S) connections (or disable them to make the crawler IPv4- or v6-only, applies to nameservers and mailservers as well)

### WEB:

- handle more messed up headers, content enconding, and broken webservers

### MAIL:

- change the structure of saved mailserver banners to match the one of saved TLSA records (ports as object keys)

## 1.4.8 (2020-07-10)

- just a fix in the e-mail banners part

## 1.4.7 (2020-07-02)

### WEB:

- handle broken `<[[CDATA` and similar sections when stripping HTML

### MAIL:

- cache the server responses by IPs, too (not just hostnames), so we make less connections overall

## 1.4.6 (2020-07-02)

### DNS and MAIL:

- use cache timeout from the config file (or a default value which got increased to an hour)

### WEB:

- better encoding autodetection

## 1.4.5 (2020-05-20)

### WEB:

- removed the output flattening option from previous version, we don't need it after all
- better content encoding autodetection without relying on `requests` or server headers (which are sometimes lying or broken)
- the detected encoding is saved with each step when saving content (`detected_encoding` field)
- the encoding autodetection uses PyICU which needs the C lib headers installed (`libicu-dev` on Debian)

## 1.4.4 (2020-04-23)

### DNS:

- configurable CH TXTs used for querying the domain's nameservers (`.results.DNS_AUTH`)
- getting TXTs for `_openid.` subdomain

### MAIL:

- configurable ports to use for TLSA records and mailserver banners (it was hardcoded to 25 originally, now defaults to 25, 465, 587)
- try to query the domain name as mailserver if there are no MX records

## WEB:

- configurable www/nonwww–ipv4/ipv6–http/https combinations to try
- configurable intermediate redirect step saving & output flattening (useful for sparklyr)
- configurable output flattening when there's just one IP and one result object (also primarily for sparklyr)

## 1.4.3 (2020-04-06)

### DNS:

- support for any domain level (from TLDs to some deep internal subdomains), initially the crawler did just 2nd level domains
- added config option to disable checking the `www.` subdomain (because it makes little sense with domains other than 2nd level…)
- fixed JSON format of nested `geoip` fields in authoritative server info (reported by Maciej Andziński‏, thanks!)

### WEB:

- disabling `www.` applies to web too, of course
- added a `final_status` field with HTTP status from the last redirect step for easier filtering/querying

## 1.4.2 (2020-03-24)

### WEB:

- added an option to save binary content if the webserver returns it for root (or redirects to it)
    - saved as base64 encoded data-uri
    - limited by `content_size_limit` (same as the text content, just bytes instead of characters)
    - a 'content_is_binary: true' field is added to the results for easy filtering
    - can be turned on/off on config, enabled by default
- added a `max_ips_per_domain` limit to help with domains that take A/AAAAs to the the extreme (> 20 records) and have broken HTTPS on webservers, so they won't fit into sane job timeouts… (unlimited by default)
- added a check to see if the IP from DNS records isn't from local range before trying to fetch web stuff from it

### GeoIP

- the local IP check applies to GeoIP, too – it makes no sense to throw addresses like `192.168.X.X` at it

## 1.4.1 (2020-03-19)

### DNS:

- if the crawler gets a CNAME when asking for a record, it saves the alias in a `cname` field, and adds `from_cname` to the final saved record (so in the end we get an IP for GeoIP lookup and we can fetch the web stuff from it… in case of A/AAAA records)
- works even for chained CNAMEs (which are generally discouraged, but people use them… some analysis of the longest chains might be interesting):
    ```
    "WEB4_www": [
        {
            "cname": "www2.helb.cz.",
            "value": null
        },
        {
            "cname": "www3.helb.cz.",
            "value": null
        },
        {
            "cname": "storage1.helb.cz.",
            "value": null
        },
        {
            "value": "5.2.67.53",
            "from_cname": "storage1.helb.cz.",
            "geoip": {
                "country": "NL",
                "org": "Liteserver Holding B.V.",
                "asn": 60404
            }
        }
    ]
    ```

### WEB:

- saved content size can be limited via `content_size_limit` in the config file, this prevents `UnpicklingError`s when reading results from Redis for extremely large websites (most of them was just a ton of comment spam…)
- various fixes for headers and encodings broken in many many different ways (people are really creative…)

### …other:

- `dns-crawler-controller` logs `UnpicklingError`s, if there are any (shouldn't be now with the limited content length, but…)
- `dns-crawler-workers` checks if there's a route (both ipv4 and 6) to the internet before starting the actual workers (which did the check anyway, but this is faster)


## 1.4 (2020-03-11)

### DNS:

- stricter checks for answer types and qnames (problem reported by Maciej Andziński‏, thanks!)
- fixed retrying the query via TCP when the response is truncated, it could run into a loop until stopped by the crawler controller when it reached the job timeout hard limit (reported by Peter Hudec… didn't happen to me in .cz, but it could, theoretically)
- TLSA records are parsed into objects for easier filtering (eg. `… | jq "…| .select(.results.DNS_LOCAL.WEB_TLSA_www.usage == 1)"`)
- all the nameserver stuff (geoip, chaos txt records) is done for all ips from server's a/aaaa records (with caching in Redis)
- support for getting additional records which aren't included in the crawler by default, so we can quick-test some ideas without touching the crawler code:
    - you can easily get some exotic stuff by just adding the record names to the config file:
        ```yaml
        dns:
        additional:
            - SPF
            - CAA
            - LOC
        ```
    - currently using this to get the legacy/deprecated SPF records, requested by Eda Rejthar from CSIRT (we were getting SPF just from TXTs until now, now it's doing both)
    - it's also pretty easy to plug in your own parsers for these records (we're using it for SPF, since we already got TXT SPFs with the same format)
    - it works with just the IN class records and just for the 2nd level domain, not any subdomains… at least for now
- added `authors.bind` and `fortune` chaos txts, we'll see if it's just taking up space or if we can use it for some version fingerprinting…


### MAIL:

- SMTP server banner fetching can now be turned off (in the config file) so people can run the crawler without getting banned by their ISPs, plus getting the banner often takes more time than everything else (all dns+web things) combined, so it might come handy to turn it off…
- that TLSA parsing works for mailservers, too (same code), we stopped getting mail/startls certificates after a brief test though (the conclusion was that it's not our business)

### WEB:

- webcrawler now follows HTTP redirects (not infinitely, it stops at 6th by default, can se set in the config file) and saves server ip, headers, cookies, certificate chain (can be turned off in config), and response content (also configurable) for each step in the redirect history (there's an `is_redirect` field in each step to allow easy filtering, and also `redirect_count` at the end)
- the `Alt-Svc` header is parsed into an object for easy filtering (eg. find websites which support quic but not http3)
- so is `Strict-Transport-Security` (so we can filter by eg. whether the `includeSubdomains` rule is enabled) and `Content-Length`
- non-standard cookie attributes (like `HttpOnly` or `SameSite`) are included in the results if the server sends them
- most of the webcrawling part is rewritten, i dug a bit into the internals of `urllib3` & `requests` and, besides seeing some trippy stuff which didn't look much like Python, found a way to keep the "session" ipv4/v6-only with a fixed source IP, while still making it work with HTTPS & SNI (so if an ipv4 website redirects us to an ipv6-only one, it should fail in the next step)
- …which also somehow fixed strange (and sometimes random) errors we were getting from some sites using CloudFlare as a proxy, i'm not completely sure what the problem was, but it works now :man_shrugging:

### certificates:

- added a certificate validity period (in days) to the result so we can filter by it easily ([Safari will cap it to 398 days soon](https://www.michalspacek.com/maximum-https-certificate-lifetime-to-be-1-year-soon))
- added a simple boolean field `is_expired` and also `expired_for` (days, it's there only if the cert is indeed expired)
- added fingerprints (for the entire cert and its associated public key) so we can check them against TLSA/DANE records (might add the tlsa check to the crawler itself in the next version, we'll see…)

### …other:

- fixed a bug when the crawler was trying to find geoip2/geolite dbs from config even when not actually using geoip, either disabled in config or running just with `--help` (reported by John Vandenberg)
- the Readme should be a bit more clear now (thanks to Láďa Lhotka)
- the cached responses (used for name and mail servers) now have a renewing TTL, so the less commonly used expire and free up some memory used by Redis (15min by default, can be set in config)
- the config file format changed a bit due to all this new stuff (if you have an older config.yaml file, the crawler will automatically update it and add the new options with defaults)
- the config is loaded by the controller and shared via Redis, so the workers on other machines use the same one (but it's still possible to override anything – useful mostly for setting different resolver IPs and GeoIP paths)
- the job creation should be much faster now (using Redis pipelines to create jobs in batches of 10k)
- `dns-crawler-workers` now uses *"soft start"* (kinda like some angle grinders :)) to make the first hit a bit easier on the system when starting a lot of workers
- the weird JSON format in the DOM dumps (reported by Maciej Andziński‏) was coming from the headless Chromium in the screenshot branch, which is now out of date again… i'll probably drop that anyway because trying to make p**Y**ppeteer (Python+asyncio interface to headless Chromium) work properly is a pain in the ass, and i'll make the screenshots using an one-off script with p**U**ppeteer (same thing in JS/Node, which inspired p**Y**ppeteer… i know JS sounds scary, but the lib actually works pretty well and is actively maintained)

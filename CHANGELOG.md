## 1.4 (2020-03-11)

### DNS:

- stricter checks for answer types and qnames (problem reported by Maciej Andzinsky, thanks!)
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
- the weird JSON format in the DOM dumps (reported by Maciej Andzinsky) was coming from the headless Chromium in the screenshot branch, which is now out of date again… i'll probably drop that anyway because trying to make p**Y**ppeteer (Python+asyncio interface to headless Chromium) work properly is a pain in the ass, and i'll make the screenshots using an one-off script with p**U**ppeteer (same thing in JS/Node, which inspired p**Y**ppeteer… i know JS sounds scary, but the lib actually works pretty well and is actively maintained)
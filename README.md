# dns-crawler

DNS crawler for getting info about a huge number of DNS domains

# Technical specification

**dns-crawler** should take as a parameter path to a text file with domain names (file can be big: 1-2M+ domain names). It should produce a file with information collected for each domain name from the input file. Output file should have structured format.


## Collecting data

Definitions:
  - `DNS_RESOLVER` - a DNS resolver operated by CZ.NIC and dedicated for **dns-crawler**
  - `DOMAINNAME` - a domain name taken from input file



For each `DOMAINNAME` data should be collected in a following sequence:

 1. DNS queries do local DNS reolver (`DNS_RESOLVER`)
 2. DNS queries do authoritative DNS servers (`DNS_AUTH`)
 3. HTTP(S) connection web servers configured for a domain name (`WEB4`,`WEB4_www`,`WEB6`,`WEB6_www`)
 4. SMTP connection mail servers configured for a domain name (`MAIL`)

###  DNS queries do local DNS reolver (`DNS_RESOLVER`)

| QUERY PARAMETERS | SAVE ANSWER AS |
| ------ | ------ |
| QTYPE = **NS**, QNAME = `DOMAINNAME` | `DNS_AUTH` |
| QTYPE = **MX**, QNAME = `DOMAINNAME`  | `MAIL` | 
| QTYPE = **A**, QNAME = `DOMAINNAME`  | `WEB4` | 
| QTYPE = **A**, QNAME = **www**.`DOMAINNAME`  | `WEB4_www` |
| QTYPE = **AAAA**, QNAME = `DOMAINNAME`  | `WEB6` | 
| QTYPE = **AAAA**, QNAME = **www**.`DOMAINNAME`  | `WEB6_www` | 
| QTYPE = **TLSA**, QNAME = **_443**.**_tcp**.`DOMAINNAME`  | `WEB_TLSA` | 
| QTYPE = **TLSA**, QNAME = **_443**.**_tcp**.**www**.`DOMAINNAME`  | `WEB_TLSA_www` | 
| QTYPE = **TLSA**, QNAME = **_25**.**_tcp**.`DOMAINNAME`  | `WEB_TLSA_www` |
| QTYPE = **DS**, QNAME = `DOMAINNAME`  | `DS` | 
| QTYPE = **DS**, QNAME = `DOMAINNAME`  | `DNSKEY` | 


All queries above should be and have **RD**+**CD**+**DO** bit set and **CLASS=IN**.


### DNS queries do authoritative DNS servers (`DNS_AUTH`)

| QUERY PARAMETERS | SAVE ANSWER AS |
| ------ | ------ |
| QTYPE = **TXT**, QNAME = **hostname.bind**, CLASS=**CHAOS** | `HOSTNAMEBIND` |
| QTYPE = **TXT**, QNAME = **version.bind**, CLASS=**CHAOS**  | `VERSIONBIND` | 


### HTTP(S) connection web servers configured for a domain name (`WEB4`,`WEB4_www`,`WEB6`,`WEB6_www`)

| CONNECTION PARAMETERS | SAVE ANSWER AS |
| ------ | ------ |
| IP=`WEB4`, server=`DOMAINNAME`, port=**80**, get software version/vendor | `WEB4_80_VERSION`, `WEB4_80_VENDOR` |
| IP=`WEB6`, server=`DOMAINNAME`, port=**80**, get software version/vendor | `WEB6_80_VERSION`, `WEB6_80_VENDOR` |
| IP=`WEB4_www`, server=**www**.`DOMAINNAME`, port=**80**, get software version/vendor | `WEB4_80_www_VERSION`, `WEB4_www_80_VENDOR` |
| IP=`WEB6_www`, server=**www**.`DOMAINNAME` port=**80**, get software version/vendor | `WEB6_80_www_VERSION`, `WEB6_www_80_VENDOR` |
| IP=`WEB4`, server=`DOMAINNAME`, port=**443**, get software version/vendor and certificate | `WEB4_443_VERSION`, `WEB4_443_VENDOR`, `WEB4_443_CERT` |
| IP=`WEB6`, server=`DOMAINNAME`, port=**443**, get software version/vendor and certificate | `WEB6_443_VERSION`, `WEB6_443_VENDOR`, `WEB6_443_CERT` |
| IP=`WEB4_www`, server=**www**.`DOMAINNAME`, port=**443**, get software version/vendor and certificate | `WEB4_443_www_VERSION`, `WEB4_www_443_VENDOR`, `WEB6_www_443_CERT` |
| IP=`WEB6_www`, server=**www**.`DOMAINNAME`, port=**443**, get software version/vendor and certificate | `WEB6_443_www_VERSION`, `WEB6_www_443_VENDOR`, `WEB4_www_443_CERT` |


### SMTP connection mail servers configured for a domain name (`MAIL`)

For each `MAIL_n` in `MAILS`:

| CONNECTION PARAMETERS | SAVE ANSWER AS |
| ------ | ------ |
| HOST=`MAIL_n`, port=**25**, get software version/vendor and certificate | `MAIL_n_VERSION`, `MAIL_n_VENDOR`, `MAIL_n_CERT` |


### Data extraction

  - from `DNSKEY` extract:
    - SEP bit
    - key algorithm
    - key length
    - ID

  - from `DS` extract:
    - digest id


  - for each signed DNS answer extract from RRSIG:
    - max* time to signature expiration (in seconds) // *max applies if there are multiple signatures

  - for each certificate extract:
	- vendor
	- key length
	- algorithm
		 
  - verify all collected TLSA RRs with coresponding certificates
   
  
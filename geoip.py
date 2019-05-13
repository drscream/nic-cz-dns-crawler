import geoip2.database

geoip_country = geoip2.database.Reader("/usr/share/GeoIP/GeoIP2-Country.mmdb")
geoip_isp = geoip2.database.Reader("/usr/share/GeoIP/GeoIP2-ISP.mmdb")

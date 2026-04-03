#!/bin/sh -f
#
# APC UPS SNMP pass-through script
# Exposes apcupsd data via SNMP with APC Enterprise OID (.1.3.6.1.4.1.318.1.1.1)
# Based on: http://zloy.pclovers.ru/2020/11/25/usb-ups-snmp/
#

# Check apcupsd is online
apcaccess -h 127.0.0.1:3551 > /dev/null 2>&1 || exit 0

PLACE=".1.3.6.1.4.1.318.1.1.1"
REQ="$2" # Requested OID

#
# Process SET requests by simply logging the assigned value
# Note that such "assignments" are not persistent,
# nor is the syntax or requested value validated
#
if [ "$1" = "-s" ]; then
    echo $* >> /tmp/passtest.log
    exit 0
fi

#
# GETNEXT requests - determine next valid instance
#
if [ "$1" = "-n" ]; then
    case "$REQ" in
    $PLACE| \
    $PLACE.0| \
    $PLACE.0.*| \
    $PLACE.1| \
    $PLACE.1.1.0*) RET=$PLACE.1.1.1.0 ;;

    $PLACE.1*| \
    $PLACE.2.0| \
    $PLACE.2.0.*| \
    $PLACE.2.1| \
    $PLACE.2.2.0*) RET=$PLACE.2.2.1.0 ;;

    $PLACE.2.2.1*) RET=$PLACE.2.2.2.0 ;;

    $PLACE.2.2.2*) RET=$PLACE.2.2.3.0 ;;

    $PLACE.2.2.3*) RET=$PLACE.2.2.4.0 ;;

    $PLACE.2*| \
    $PLACE.3.0*| \
    $PLACE.3.1*| \
    $PLACE.3.2.0*) RET=$PLACE.3.2.1.0 ;;

    $PLACE.3.2.1*| \
    $PLACE.3.2.2*| \
    $PLACE.3.2.3*) RET=$PLACE.3.2.4.0 ;;

    $PLACE.3.2.4*) RET=$PLACE.3.2.5.0 ;;

    $PLACE.3.2*| \
    $PLACE.4.0*| \
    $PLACE.4.1*| \
    $PLACE.4.2.0*) RET=$PLACE.4.2.1.0 ;;

    $PLACE.4.2.1*) RET=$PLACE.4.2.2.0 ;;

    $PLACE.4.2.2*) RET=$PLACE.4.2.3.0 ;;

    $PLACE.4.2.3*) RET=$PLACE.4.2.4.0 ;;

    $PLACE.4.2.*| \
    $PLACE.5*| \
    $PLACE.6*| \
    $PLACE.7.0*| \
    $PLACE.7.1*| \
    $PLACE.7.2.0*| \
    $PLACE.7.2.1*| \
    $PLACE.7.2.2*) RET=$PLACE.7.2.3.0 ;;

    $PLACE.7.2.3*) RET=$PLACE.7.2.4.0 ;;

    $PLACE.7*| \
    $PLACE.8.0*) RET=$PLACE.8.1.0 ;;

    *) exit 0 ;;
    esac
else
#
# GET requests - check for valid instance
#
    case "$REQ" in
    $PLACE.1.1.1.0| \
    $PLACE.2.2.1.0| \
    $PLACE.2.2.2.0| \
    $PLACE.2.2.3.0| \
    $PLACE.2.2.4.0| \
    $PLACE.3.2.1.0| \
    $PLACE.3.2.4.0| \
    $PLACE.3.2.5.0| \
    $PLACE.4.2.1.0| \
    $PLACE.4.2.2.0| \
    $PLACE.4.2.3.0| \
    $PLACE.4.2.4.0| \
    $PLACE.7.2.3.0| \
    $PLACE.7.2.4.0| \
    $PLACE.8.1.0) RET=$REQ ;;
    *) exit 0 ;;
    esac
fi

#
# "Process" GET* requests - return hard-coded value
#
echo "$RET"
case "$RET" in
    $PLACE.1.1.1.0) echo "string"; apcaccess -h 127.0.0.1:3551 -u -p MODEL ; exit 0 ;;
    $PLACE.2.2.1.0) echo "Gauge32"; apcaccess -h 127.0.0.1:3551 -u -p BCHARGE ; exit 0 ;;
    $PLACE.2.2.2.0) echo "Gauge32"; apcaccess -h 127.0.0.1:3551 -u -p ITEMP ; exit 0 ;;
    $PLACE.2.2.3.0) echo "Timeticks"; echo $(($(LC_ALL=C printf "%.*f" 0 $(apcaccess -h 127.0.0.1:3551 -u -p TIMELEFT)) * 6000)) ; exit 0 ;;
    $PLACE.2.2.4.0) echo "string"; apcaccess -h 127.0.0.1:3551 -u -p BATTDATE ; exit 0 ;;
    $PLACE.3.2.1.0) echo "Gauge32"; apcaccess -h 127.0.0.1:3551 -u -p LINEV ; exit 0 ;;
    $PLACE.3.2.4.0) echo "Gauge32"; apcaccess -h 127.0.0.1:3551 -u -p LINEFREQ ; exit 0 ;;
    $PLACE.3.2.5.0) echo "string"; apcaccess -h 127.0.0.1:3551 -u -p LASTXFER ; exit 0 ;;
    $PLACE.4.2.1.0) echo "Gauge32"; apcaccess -h 127.0.0.1:3551 -u -p OUTPUTV ; exit 0 ;;
    $PLACE.4.2.2.0) echo "Gauge32"; apcaccess -h 127.0.0.1:3551 -u -p LINEFREQ ; exit 0 ;;
    $PLACE.4.2.3.0) echo "Gauge32"; apcaccess -h 127.0.0.1:3551 -u -p LOADPCT ; exit 0 ;;
    $PLACE.4.2.4.0) echo "Gauge32"; apcaccess -h 127.0.0.1:3551 -u -p LOADPCT ; exit 0 ;;
    $PLACE.7.2.3.0) echo "string"; apcaccess -h 127.0.0.1:3551 -u -p SELFTEST ; exit 0 ;;
    $PLACE.7.2.4.0) echo "string"; apcaccess -h 127.0.0.1:3551 -u -p SELFTEST ; exit 0 ;;
    $PLACE.8.1.0) echo "Gauge32"; echo 1 ; exit 0 ;;
    *) echo "string"; echo "ack... $RET $REQ"; exit 0 ;; # Should not happen
esac

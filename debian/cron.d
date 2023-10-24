#
# cron jobs for wazo-call-logs
#

25 4 * * * root . /etc/profile.d/xivo_uuid.sh && /usr/bin/wazo-call-logs
43 3 * * * root /usr/bin/wazo-call-logd-sync-db --quiet

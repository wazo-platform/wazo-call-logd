#
# cron jobs for wazo-call-logs
#

25 4 * * * root source /etc/profile.d/xivo_uuid.sh && /usr/bin/wazo-call-logs

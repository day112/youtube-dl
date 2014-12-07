# encoding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    month_by_name,
    int_or_none,
)

class ScreenwaveMediaIE(InfoExtractor):
    _VALID_URL = r'(?:http://)?(?' \
        r':(?P<generic>player\.screenwavemedia\.com/play/[a-zA-Z]+\.php\?[^"]*\bid=(?P<video_id>.+))' \
        r'|(?P<cinemassacre>(?:www\.)?cinemassacre\.com/(?P<cm_date_Y>[0-9]{4})/(?P<cm_date_m>[0-9]{2})/(?P<cm_date_d>[0-9]{2})/(?P<cm_display_id>[^?#/]+))' \
        r'|(?P<teamfourstar>(?:www\.)?teamfourstar\.com/video/(?P<tfs_display_id>[a-z0-9\-]+)/?)' \
        r')'

    _TESTS = [
        {
            'url': 'http://cinemassacre.com/2012/11/10/avgn-the-movie-trailer/',
            'md5': 'fde81fbafaee331785f58cd6c0d46190',
            'info_dict': {
                'id': 'Cinemasssacre-19911',
                'ext': 'mp4',
                'upload_date': '20121110',
                'title': '“Angry Video Game Nerd: The Movie” – Trailer',
                'description': 'md5:fb87405fcb42a331742a0dce2708560b',
            },
        },
        {
            'url': 'http://cinemassacre.com/2013/10/02/the-mummys-hand-1940',
            'md5': 'd72f10cd39eac4215048f62ab477a511',
            'info_dict': {
                'id': 'Cinemasssacre-521be8ef82b16',
                'ext': 'mp4',
                'upload_date': '20131002',
                'title': 'The Mummy’s Hand (1940)',
            },
        }
    ]

    def _cinemassacre_get_info(self, url):
        mobj = re.match(self._VALID_URL, url)
        display_id = mobj.group('cm_display_id')

        webpage = self._download_webpage(url, display_id)
        video_date = mobj.group('cm_date_Y') + mobj.group('cm_date_m') + mobj.group('cm_date_d')
        mobj = re.search(r'src="(?P<embed_url>http://player\.screenwavemedia\.com/play/[a-zA-Z]+\.php\?[^"]*\bid=.+?)"', webpage)
        if not mobj:
            raise ExtractorError('Can\'t extract embed url and video id')
        playerdata_url = mobj.group('embed_url')

        video_title = self._html_search_regex(
            r'<title>(?P<title>.+?)\|', webpage, 'title')
        video_description = self._html_search_regex(
            r'<div class="entry-content">(?P<description>.+?)</div>',
            webpage, 'description', flags=re.DOTALL, fatal=False)
        video_thumbnail = self._og_search_thumbnail(webpage)

        return {
            'title': video_title,
            'description': video_description,
            'upload_date': video_date,
            'thumbnail': video_thumbnail,
            '_embed_url': playerdata_url,
        }

    def _teamfourstar_get_info(self, url):
        mobj = re.match(self._VALID_URL, url)
        display_id = mobj.group('tfs_display_id')
        webpage = self._download_webpage(url, display_id)

        mobj = re.search(r'src="(?P<embed_url>http://player\.screenwavemedia\.com/play/[a-zA-Z]+\.php\?[^"]*\bid=.+?)"', webpage)
        if not mobj:
            raise ExtractorError('Can\'t extract embed url and video id')
        playerdata_url = mobj.group('embed_url')

        video_title = self._html_search_regex(
            r'<div class="heroheadingtitle">(?P<title>.+?)</div>', webpage, 'title')
        video_date = self._html_search_regex(
            r'<div class="heroheadingdate">(?P<date>.+?)</div>', webpage, 'date')
        mobj = re.match('(?P<month>[A-Z][a-z]+) (?P<day>\d+), (?P<year>\d+)', video_date)
        video_date = '%04u%02u%02u' % (int(mobj.group('year')), month_by_name(mobj.group('month')), int(mobj.group('day')))
        video_description = self._html_search_regex(
            r'<div class="postcontent">(?P<description>.+?)</div>', webpage, 'description', flags=re.DOTALL)
        video_thumbnail = self._og_search_thumbnail(webpage)

        return {
            'title': video_title,
            'description': video_description,
            'upload_date': video_date,
            'thumbnail': video_thumbnail,
            '_embed_url': playerdata_url,
        }

    def _screenwavemedia_get_info(self, url):
        mobj = re.match(self._VALID_URL, url)
        if not mobj:
            raise ExtractorError('Can\'t extract embed url and video id')
        video_id = mobj.group('video_id')

        playerdata = self._download_webpage(url, video_id, 'Downloading player webpage')

        vidtitle = self._search_regex(
            r'\'vidtitle\'\s*:\s*"([^\']+)"', playerdata, 'vidtitle').replace('\\/', '/')
        vidurl = self._search_regex(
            r'\'vidurl\'\s*:\s*"([^\']+)"', playerdata, 'vidurl').replace('\\/', '/')
        pageurl = self._search_regex(
            r'\'pageurl\'\s*:\s*"([^\']+)"', playerdata, 'pageurl', fatal=False).replace('\\/', '/')

        videolist_url = None

        mobj = re.search(r"'videoserver'\s*:\s*'(?P<videoserver>[^']+)'", playerdata)
        if mobj:
            videoserver = mobj.group('videoserver')
            mobj = re.search(r'\'vidid\'\s*:\s*"(?P<vidid>[^\']+)"', playerdata)
            vidid = mobj.group('vidid') if mobj else video_id
            videolist_url = 'http://%s/vod/smil:%s.smil/jwplayer.smil' % (videoserver, vidid)
        else:
            mobj = re.search(r"file\s*:\s*'(?P<smil>http.+?/jwplayer\.smil)'", playerdata)
            if mobj:
                videolist_url = mobj.group('smil')

        if videolist_url:
            videolist = self._download_xml(videolist_url, video_id, 'Downloading videolist XML')
            formats = []
            baseurl = vidurl[:vidurl.rfind('/') + 1]
            for video in videolist.findall('.//video'):
                src = video.get('src')
                if not src:
                    continue
                file_ = src.partition(':')[-1]
                width = int_or_none(video.get('width'))
                height = int_or_none(video.get('height'))
                bitrate = int_or_none(video.get('system-bitrate'))
                format = {
                    'url': baseurl + file_,
                    'format_id': src.rpartition('.')[0].rpartition('_')[-1],
                }
                if width or height:
                    format.update({
                        'tbr': bitrate // 1000 if bitrate else None,
                        'width': width,
                        'height': height,
                    })
                else:
                    format.update({
                        'abr': bitrate // 1000 if bitrate else None,
                        'vcodec': 'none',
                    })
                formats.append(format)
            self._sort_formats(formats)
        else:
            formats = [{
                'url': vidurl,
            }]

        return {
            'id': video_id,
            'title': vidtitle,
            'formats': formats,
            '_episode_page': pageurl,
        }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)

        swm_info = None
        site_info = None

        if mobj.group('generic'):
            swm_info = self._screenwavemedia_get_info(url)
            url = swm_info['_episode_page']
            mobj = re.match(self._VALID_URL, url)

        if mobj:
            if mobj.group('cinemassacre'):
                site_info = self._cinemassacre_get_info(url)
            elif mobj.group('teamfourstar'):
                site_info = self._teamfourstar_get_info(url)

        if not swm_info:
            if site_info:
                swm_info = self._screenwavemedia_get_info(site_info['_embed_url'])

        if not swm_info:
            raise ExtractorError("Failed to extract metadata for this URL")

        if site_info:
            swm_info.update(site_info)

        return swm_info

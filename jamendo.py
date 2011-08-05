#!/usr/bin/env python

import json
import optparse
import sys
import xml.sax
import os

def intersection(list_of_lists):
    """
    Finds any element that is present in all the lists
    """
    first_list = list_of_lists[0]
    other_lists = list_of_lists[1:]
    result = []
    for item in first_list:
        if not all([item in other_list for other_list in other_lists]):
            continue
        result.append(item)
    return result

def union(list_of_lists):
    """
    Makes a list that consist of all the elements
    present in any of the lists. If an element is present
    in more than onelist, it only appears once.
    """
    result = []
    for list in list_of_lists:
        result.extend([item for item in list if item not in result])
    return result

class MyGrabber(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.intag = []
        self.artistcount = 0
        self.in_artist = None
        self.in_album = None
        self.in_track = None
        self.track_data = {}
        self.tagged_tracks = {}
    def startElement(self, name, attrs):
        self.intag.append(name)
    def endElement(self, name):
        assert self.intag[-1] == name
        self.intag = self.intag[:-1]
        if name == "track":
            self.track_data = {}
    def characters(self, content):
        if self.intag[-1] == "id" and self.intag[-2] == "artist":
            self.artistcount += 1
            sys.stderr.write("%s\r" % (self.artistcount,))
            self.in_artist = content
        elif self.intag[-1] == "id" and self.intag[-2] == "album":
            self.in_album = content
        elif self.intag[-1] == "id" and self.intag[-2] == "track":
            self.in_track = content
        elif self.intag[-2] == "track":
            self.track_data[self.intag[-1]] = content
        elif self.intag[-1] == "idstr" and self.intag[-2] == "tag":
            self.tagged_tracks.setdefault(content, []).append([self.in_artist, self.in_album, self.in_track])

class Analyser(object):
    def __init__(self, filename):
        self.filename = filename
        self.data = None

    def loadjson(self):
        if not self.data:
            with open(self.filename, "rb") as fp:
                self.data = json.load(fp)
        return self.data

    def findtracks(self, album = None, tags = [], cumulative_tags = True):
        data = self.loadjson()
        if tags:
            if cumulative_tags:
                return intersection([data[tag] for tag in tags])
            else:
                return union([data[tag] for tag in tags])
        elif album:
            tracks = []
            for tag, tagtracks in data.iteritems():
                for track in tagtracks:
                    if track[1] == album and track[2] not in [t[2] for t in tracks]:
                        tracks.append(track)
            return tracks

    def makeplaylist(self, itemlist):
        MP3STREAM = "http://api.jamendo.com/get2/stream/track/redirect/?id=%s&streamencoding=mp31"
        OGGSTREAM = "http://api.jamendo.com/get2/stream/track/redirect/?id=%s&streamencoding=ogg2"
        TRACKDATA = "http://www.jamendo.com/fr/track/%s"
        return u"\n".join([MP3STREAM % (id_track,) for id_artist, id_album, id_track in itemlist])

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("--json", dest="json_filename", default="jamendo.json",
                      help="The JSON file used to store the cached Jamendo DB")
    parser.add_option("--xml", dest="xml_filename", default="dbdump_artistalbumtrack.xml",
                      help="The XML file downloaded from Jamendo")
    parser.add_option("--any", action="store_false", dest="cumulative_tags", default=True, help="Allow the playlist to contain tracks with any of the tags (all by default)")
    parser.add_option("-t", "--tag", action="append", dest="tags", default=[], help="Tracks in the playlist must have this tag (you can add many -t options)")
    parser.add_option("-o", "--output", dest="output_filename", help="Playlist file to create")
    parser.add_option("-j", "--makejson", action="store_true",dest="makejson", default=False,help="Generate the JSON file from the XML file")
    parser.add_option("-l", "--list-tags", action="store_true",dest="list_tags", default=False,help="List existing tags")
    parser.add_option("-a", "--album", dest="album", help="Album ID to create playlist from")
    options, args = parser.parse_args()
    tags = options.tags
    if options.makejson or not os.path.exists(options.json_filename):
        print "Generate JSON file from XML file"
        grabber = MyGrabber()
        xml.sax.parse(options.xml_filename, grabber)
        with open(options.json_filename, "wb") as fp:
            json.dump(grabber.tagged_tracks, fp)
        print "DONE."
    jamendo = Analyser(options.json_filename)
    playlist_filename = options.output_filename
    if options.list_tags:
        jamendo.loadjson()
        for tag,tracks in jamendo.data.iteritems():
            print "%5.5s %75.75s" % (len(tracks), tag)
    if tags:
        if not playlist_filename:
            playlist_filename = "%s.m3u" % ("_".join(tags),)
        tracks = jamendo.findtracks(tags = tags, cumulative_tags = options.cumulative_tags)
        with open(playlist_filename, "wb") as fp:
            fp.write(jamendo.makeplaylist(tracks))
            fp.write("\n")
        print "Playlist wrote to %s (%s tracks)" % (playlist_filename, len(tracks))
    if options.album:
        if not playlist_filename:
            playlist_filename = "album_%s.m3u" % (options.album,)
        tracks = jamendo.findtracks(album = options.album)
        with open(playlist_filename, "wb") as fp:
            fp.write(jamendo.makeplaylist(tracks))
            fp.write("\n")
        print "Playlist wrote to %s (%s tracks)" % (playlist_filename, len(tracks))

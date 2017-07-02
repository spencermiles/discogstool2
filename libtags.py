import mutagen
import sys
import pprint
import urllib.request, urllib.parse, urllib.error
import os.path
import shutil
import filecmp
import re
from mutagen.id3 import ID3
import client_interface

whitelist = frozenset([i for i in "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ[]()-_+.' "])

def sanitize(fn):
    return "".join([i if (i in whitelist) else "_" for i in fn])

tag_map = {
    "ID3" : {
        "album" : "TALB",
        "artist" : "TPE1",
        "bpm" : "TBPM",
        "title" : "TIT2",
        "year" : "TDRC",
        "comment" : "COMM::'eng'",
        "genre" : "TCON",
        "image" : "APIC",
        "track" : "TRCK",
        "label" : "TPUB",
        "compilation" : "TCMP",
        },
    "MP4Tags" : {
        "album" : "\xa9alb",
        "artist" : "\xa9ART",
        "bpm" : "tmpo",
        "title" : "\xa9nam",
        "year" : "\xa9day",
        "comment" : "\xa9cmt",
        "genre" : "\xa9gen",
        "image" : "covr",
        "track" : "trkn",
        "label" : "\xa9lab",
        "compilation" : "cpil",
    }
}

rev_tag_map = {}
for k,v in tag_map.items():
    rev_tag_map[k] = {}
    for k2,v2 in tag_map[k].items():
        rev_tag_map[v2] = k2

uni_flag = "\xa9"

old_comment_regex = re.compile(r"([0-9]+) VERIFIED");
comment_regex = re.compile(r".* Discogs: ([0-9]+)");

class TagsException(Exception):
    pass

def track_from_comment(comment, index):
    m = comment_regex.match(comment)
    if not m:
        m = old_comment_regex.match(comment)

    if not m:
        raise TagsException("comment '%s' doesn't specify a release" % comment)

    return client_interface.DiscogsTrack(int(m.groups()[0]), index - 1)


class AudioFile(object):
    def __init__(self, filename, track=None):
        self.filename = filename
        self.obj = mutagen.File(filename)
        if self.obj == None:
            raise TagsException("mutagen couldn't open " + filename)

        if not self.obj.tags:
            self.obj.add_tags()

        if issubclass(self.obj.tags.__class__, mutagen.id3.ID3):
            self.tagstype = "ID3"
        else:
            self.tagstype = self.obj.tags.__class__.__name__

        if not track:
            if not self["comment"] or not self["track"]:
                raise TagsException("file has no comment or track number information")

            track = track_from_comment(self["comment"], self["track"][0])

            if self["track"][1] != track.getRelease().getTotalTracks():
                raise TagsException("total tracks mismatch")

        self.update(track)

    def getTrack(self):
        return self.track

    def getFilename(self):
        return self.filename

    def __getitem__(self, key):
        if key == "filename":
            return self.filename
        try:
            i = self.obj.tags[tag_map[self.tagstype][key]]
        except KeyError:
            return None
        while isinstance(i, list):
            i = i[0]
        if key == "track":
            i = str(i).split("/")
            if len(i) == 1:
                i.append(0)
            i = tuple([int(x) for x in i])
        elif key == "bpm":
            i = int(str(i))
        elif key == "image":
            i = "<binary>"
        else:
            i = str(i)
        return i

    def update(self, track):
        release = track.release

        self["artist"] = track.getArtist()
        self["album"] = release.getTitle()
        self["title"] = track.getTitle()
        self["year"] = release.getYear()
        self["comment"] = "%s [%s] Discogs: %d" % (release.getLabel(),
                release.getCatno(), release.getId())
        self["label"] = release.getLabel()
        self["track"] = (track.getTrackNumber(), release.getTotalTracks())
        if "image" not in list(self.keys()):
            i = release.getArtwork()
            if i:
                self["image"] = i
        if release.isCompilation():
            self["compilation"] = 1
        self.track = track

    def commit(self):
        self.save()

    def __setitem__(self, key, value):
        mkey = tag_map[self.tagstype][key]
        if self.tagstype == "ID3":

            clazz = getattr(mutagen.id3, mkey[:4])
            if mkey == "COMM::'eng'":
                value = clazz(encoding=3, desc="", lang='eng', text=value)
            elif mkey == "APIC":
                value = clazz(type=0, encoding=0, mime="image/jpeg", data=value)
            else:
                if mkey == "TRCK":
                    if value[1]:
                        value = "%d/%d" % value
                    else:
                        value = str(value[0])
                elif mkey == "TCMP":
                    value = str(value)
                # mutagen id3 can't seem to handle unicode values
                value = clazz(encoding=3, text=value)
        elif self.tagstype == "MP4Tags":
            if mkey == "trkn":
                value = [value]

        self.obj.tags[mkey] = value

    def save(self):
        self.obj.save()

    def keys(self):
        ok = list(self.obj.tags.keys())
        ret = []
        for k,v in tag_map[self.tagstype].items():
            if v in ok:
                ret.append(k)
        return ret

    def __str__(self):
        ret = {}
        for k in list(self.keys()):
            ret[k] = self[k]
        return repr(ret)

    def rename_file(self, destdir, verbose, dryrun, move, withgenre):
        af = self
        ext = self.filename.rsplit(".", 1)[1]
        if withgenre:
            if af["genre"] == "null":
                print(("Skipping genre unassigned", self.filename))
                return
            newdir = os.path.join(destdir, sanitize(str(af["genre"])))
        else:
            newdir = destdir

        try:
            bpm = int(str(af["bpm"]))
        except ValueError:
            bpm = 0
        if withgenre:
            newfn = sanitize("[%03d] %s - %s %d (%s).%s" % 
                    (bpm, af["artist"], af["title"], af["track"][0], af["year"], ext))
        else:
            newfn = sanitize("%s - %s %d [%s].%s" %
                    (af["artist"], af["title"], af["track"][0], af["label"], ext))

        newpath = os.path.abspath(os.path.join(newdir, newfn))
        if not os.path.exists(newpath) or not filecmp.cmp(self.filename, newpath):
            if verbose:
                print("MOVE" if move else "COPY", self.filename, "\n\t-->", newpath)
            if not dryrun:
                if not os.path.exists(newdir):
                    os.makedirs(newdir)
                if move:
                    shutil.move(self.filename, newpath)
                    self.filename = newpath
                else:
                    shutil.copy2(self.filename, newpath)
        else:
            if verbose:
                print("Skipping unchanged file", newpath)
        return newpath

# debugging only
def main():
    for filename in sys.argv[1:]:
        af = AudioFile(filename)
        print(filename)
        for k in list(af.keys()):
            if k not in ["image"]:
                print("%s: '%s'" % (k, af[k]))

if __name__ == "__main__":
    main()

# discogstool2

A Python toolkit for digitizing vinyl records and managing your music collection with automatic metadata tagging from Discogs.

## Overview

discogstool2 helps you process audio recordings from vinyl records and automatically tag them with accurate metadata from the Discogs database. It can split multi-track WAV files, normalize audio levels, convert between formats, and organize your collection.

## Features

- **Automatic Metadata Tagging**: Fetches release and track information from Discogs API
- **Multi-track WAV Splitting**: Automatically splits single WAV files into individual tracks using cue markers
- **Audio Processing**: Normalizes volume levels and converts to AIFF format
- **Collection Management**: Compare your local files against your Discogs collection
- **Cover Art**: Automatically downloads and embeds album artwork
- **Format Support**: Handles WAV, FLAC, MP3, M4A, AAC, and AIFF files
- **Local Caching**: SQLite database caches Discogs API responses to minimize API calls

## Prerequisites

### System Dependencies

You need the following command-line tools installed:

- **ffmpeg**: Audio conversion (`brew install ffmpeg` on macOS, `apt install ffmpeg` on Ubuntu)
- **normalize-audio** or **normalize**: Audio normalization (`brew install normalize` on macOS, `apt install normalize-audio` on Ubuntu)
- **flac**: FLAC decoding (`brew install flac` on macOS, `apt install flac` on Ubuntu)

### Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- mutagen (audio metadata handling)
- tqdm (progress bars)
- python3-discogs-client (Discogs API integration)
- numpy (audio data processing)
- urllib3 (HTTP requests)

### Discogs Account

You need a Discogs account. On first run, the tool will:
1. Display an authorization URL
2. Ask you to visit the URL and authorize the application
3. Prompt you to enter the verification code
4. Store your credentials in `~/.discogstool/discogs_auth`

## Installation

1. Clone this repository
2. Install system dependencies (ffmpeg, normalize, flac)
3. Install Python dependencies: `pip install -r requirements.txt`
4. Make the scripts executable: `chmod +x dt_process dt_collection`

## Recording Workflow

**Important**: This tool does NOT record audio from your turntable. It's a post-processing tool that works with audio files you've already captured. Here's the complete workflow:

### Step 1: Record the Vinyl

Use audio recording software like **Audacity** (free, cross-platform):

1. Connect your turntable to your computer via audio interface/USB
2. Open Audacity and start recording
3. Play the entire side of the record
4. Stop recording when the side finishes

### Step 2: Add Cue Markers (Recommended Method)

For the best workflow, mark where each track starts:

1. In Audacity, listen through and place a **label** (Ctrl+B or Cmd+B) at the beginning of each track
2. The label names don't matter - the tool only uses their positions
3. You should have one label per track on the release

### Step 3: Export the Audio

**Option A: Multi-track WAV (Recommended)**
1. File → Export → Export Audio
2. Choose WAV format
3. Name the file: `[r{RELEASE_ID}].wav`
   - Example: `[r12345678].wav`
   - Find the release ID from the Discogs URL: `https://www.discogs.com/release/12345678-...`
4. The cue markers will be embedded in the WAV file

**Option B: Individual Track Files**
1. Select the audio for each track individually
2. File → Export → Export Selected Audio
3. Name each file: `{RELEASE_ID}{POSITION}.wav`
   - Examples: `12345678A1.wav`, `12345678A2.wav`, `12345678B1.wav`
4. No cue markers needed with this method

### Step 4: Process with dt_process

Now use this tool to split (if needed), normalize, tag, and organize:

```bash
./dt_process -o ~/Music/Processed '[r12345678].wav'
```

The tool will:
- Split the WAV using your cue markers (Option A) or process individual files (Option B)
- Fetch metadata from Discogs
- Normalize audio levels
- Convert to AIFF format
- Embed cover art
- Tag with all metadata (artist, title, year, label, etc.)
- Rename files appropriately

### Alternative Recording Software

You can use any audio recording software that supports:
- WAV export (required)
- Cue markers/labels (optional, for multi-track workflow)

Examples: Adobe Audition, Reaper, Sound Forge, GarageBand, etc.

## Usage

### Processing Audio Files (dt_process)

Convert and tag audio files with Discogs metadata.

#### File Naming Convention

Files must follow specific naming patterns to identify the Discogs release and track position:

**For individual tracks:**
```
{RELEASE_ID}{POSITION}.{EXTENSION}
```
Examples:
- `12345678A1.wav` - Release 12345678, track A1
- `12345678B.flac` - Release 12345678, track B
- `12345678A2.mp3` - Release 12345678, track A2

**For multi-track WAV files (to be split):**
```
[r{RELEASE_ID}].wav
```
Example:
- `[r12345678].wav` - Will be split into individual tracks based on cue markers

#### Basic Usage

```bash
./dt_process -o /path/to/output/directory file1.wav file2.flac [r12345].wav
```

#### Options

- `-o, --outdir` (required): Output directory for processed files
- `-v, --verbose`: Enable debug messages
- `-j, --jobs N`: Number of parallel jobs (default: CPU count, Linux only)

#### Examples

Process a single track:
```bash
./dt_process -o ~/Music/Processed 12345678A1.wav
```

Process multiple files:
```bash
./dt_process -o ~/Music/Processed 12345678A1.wav 12345678A2.wav 12345678B1.flac
```

Split and process a multi-track WAV file:
```bash
./dt_process -o ~/Music/Processed '[r12345678].wav'
```

#### What dt_process Does

1. **For WAV files with cue markers** (named `[rXXXX].wav`):
   - Reads cue markers from the WAV file
   - Splits into individual tracks (minimum 30 seconds, or 6 seconds for releases with many short tracks)
   - Creates temporary files named `{RELEASE_ID}.{POSITION}.wav`

2. **For all audio files**:
   - Fetches metadata from Discogs (artist, album, track title, year, genre, label, etc.)
   - For WAV/FLAC: Normalizes audio to -1.5dB peak, converts to 44.1kHz/16-bit AIFF
   - For MP3: Copies and tags without re-encoding
   - Embeds cover artwork
   - Renames files to: `{ARTIST} - {TITLE} {TRACK_NUM} [{LABEL}].{ext}`

### Managing Your Collection (dt_collection)

Analyze your music collection and compare it against your Discogs collection.

#### Basic Usage

```bash
./dt_collection /path/to/music/directory
```

#### Options

- `-c, --collection FILE`: CSV file exported from your Discogs collection
- `-u, --update-metadata`: Refresh metadata/images from Discogs for all found files
- `-n, --dry-run`: Show what would be done without making changes
- `-v, --verbose`: Output diagnostic messages
- `-Y, --min-year YEAR`: Ignore releases older than specified year

**Report options** (requires `-c`):
- `-a, --all-reports`: Generate all reports
- `-M, --missing`: Report tracks found locally but not in Discogs collection
- `-D, --discogs-missing`: Report releases in Discogs collection not found locally
- `-P, --partially-recorded`: Report releases that are only partially recorded

#### Examples

Scan a directory and update metadata:
```bash
./dt_collection -u ~/Music/Vinyl
```

Compare local files to Discogs collection:
```bash
./dt_collection -c ~/Downloads/collection.csv ~/Music/Vinyl
```

Generate all reports:
```bash
./dt_collection -c ~/Downloads/collection.csv -a ~/Music/Vinyl
```

Find what you haven't recorded yet:
```bash
./dt_collection -c ~/Downloads/collection.csv -D ~/Music/Vinyl
```

Dry run to see what would be updated:
```bash
./dt_collection -n -u ~/Music/Vinyl
```

#### Exporting Your Discogs Collection

1. Go to https://www.discogs.com/settings/exports
2. Request a new export
3. Download the CSV file when ready
4. Use this file with the `-c` option

## How It Works

### File Format and Metadata

Audio files are tagged with metadata stored in the comment field:
```
{LABEL} [{CATALOG_NUMBER}] Discogs: {RELEASE_ID}
```

This allows the tool to:
- Identify which Discogs release a file belongs to
- Refresh metadata when the release data changes
- Verify track counts match the release

### Data Storage

The tool creates a directory at `~/.discogstool/` containing:
- `discogs_auth`: OAuth tokens for Discogs API
- `discogs.db`: SQLite database caching API responses (7-day default cache)
- Cover art images (hashed by URI)

### Position Matching

The tool handles various track position formats:
- Standard: A1, A2, B1, B2
- Without numbers: A, B (treated as A1, B1)
- Double-sided: AA1, AA2 (for side B on some pressings)
- Alternative formats: 1B instead of B1
- With periods: A1., B2.

## Limitations

- **Multiprocessing**: Parallel processing (`-j` option) only works on Linux due to multiprocessing limitations on macOS/Windows
- **Cue Markers**: Multi-track WAV splitting requires properly formatted cue markers in the WAV file
- **API Rate Limiting**: Discogs API has rate limits (the tool includes delays to handle this)
- **File Format**: Only processes files in supported formats (WAV, FLAC, MP3, M4A, AAC, AIFF)

## Troubleshooting

**"missing normalize utility"**
- Install normalize-audio (Ubuntu) or normalize (macOS)

**"Release XXXXX not found"**
- Verify the release ID exists on Discogs
- Check your internet connection
- The release may have been deleted or merged on Discogs

**"Unexpected region count"**
- The number of cue markers doesn't match the track count on Discogs
- Verify your cue markers are correct
- Check that the Discogs tracklist is accurate

**"Couldn't find position X in release Y"**
- The track position in your filename doesn't exist in the Discogs release
- Check the tracklist on Discogs and verify your position labels

**Rate limiting errors**
- The tool includes automatic retry logic and delays
- If persistent, wait a few minutes and try again

## License

See LICENSE file for details.
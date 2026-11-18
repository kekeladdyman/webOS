# Dead Mount Death Play edit — project files

Source for the 38s edit set to "Ain't No Mountain High Enough". Media is not stored here.

## Rebuild
1. Put the 12 episodes (1080p, English dub on audio track 0) in `eps/ep01.mkv` … `eps/ep12.mkv`
   (they came from the "Dead Mount Death Play" folder in Google Drive).
2. Song: the audio of the reference clip, trimmed to 0–36.18s, as `audio/song.wav` (48 kHz stereo);
   beat data in `audio/song_analysis.json` (librosa `beat_track`, key `beats`).
3. Dialogue stems: run Demucs (`htdemucs --two-stems vocals`) on the dub windows listed in the notes below
   into `dlg/sep/htdemucs/raw_*/vocals.wav`.
4. Fonts in `fonts/`: Anton, PlayfairItalic, CormorantItalic, Cinzel, Oswald (Google Fonts).
5. `python extract.py` → `python audio_mix.py` → `python render.py final` → mux `out/final_video.mp4` + `out/mix.wav`.

`tl.py` is the timeline (shots, captions, lyric text); `render.py` draws frames; `audio_mix.py` builds the soundtrack.

## Version 2 and 3 (same script files; version 3 is current)
`tl2.py` timeline · `r2core.py` engine (3D planes, cut-out mattes, styled text) · `render2.py` scenes · `audio2.py` soundtrack with effects ·
`prep2.py` clip extraction + character mattes (rembg `isnet-anime`).
Run: `python prep2.py` → `python audio2.py` → `python render2.py final` → mux `out/final2_video.mp4` + `out/mix2.wav`.
Sound effects are Mixkit free-licence files saved as `sfx/<id>.wav` (ids and timings in `audio2.py`; measurements in `sfx/analysis.json`;
`https://assets.mixkit.co/active_storage/sfx/<id>/<id>.wav`). Extra fonts are listed in the notes below.

# DMDP edit — working notes (shot ids = shots/epXX.json index; times mm:ss in episode)

## Song (uploads/b6fe2d68...mp4 -> audio/song.wav)
- "Ain't No Mountain High Enough", 129.2 BPM, beats in audio/song_analysis.json, lyrics w/ times in audio/song_words.json
- usable 0.00-35.0s. Song fades 33.3->35.0. 35.1-36.2 is the TikTok outro jingle (full-scale) -> MUST CUT. Song is quiet in file (RMS ~-28dB) -> normalise.
- intro instrumental 0-5.5; "Listen, baby" 5.52; verse 7.44-15.5 (mountain 9.0 / valley 10.9 / river 12.8 / enough 14.1);
  "If you need me call me" 15.5-18; "No matter where you are" 18.08; "No matter how far" 19.88; "Don't worry baby" 21.74;
  "Just call my name" 23.4; "I'll be there in a hurry" 25.2; "You don't have to worry" 27.2; "Oh baby there" 29.04;
  "Ain't no mountain high enough" 30.28-33.3 (chorus hit); "Ain't no.." 33.3-35 fade.

## Dialogue (English dub = audio track 0), times in seconds in episode
- OPEN: E02 66.24-69.16 "All I wanted was peace." + 70.54-71.30 "Nothing more."   (alt: E02 35.02-36.96 "I desired only peace.")
- MID (before chorus ~28.3): E05 1077.78-1079.74 "I'll protect you, no matter what."
- CLOSE: E05 1411.56-1414.22 "I suppose I can't go dying just yet." ("Well then," at 1409.70-1410.88)
- spare: E01 682.90-685.10 "It seems this land I've arrived in is peaceful."; E01 424.92-427.68 "Lives are no more than playthings to me.";
  E12 1177.64-1180.90 "This world is so very, very beautiful."
- demucs stems: dlg/sep/htdemucs/raw_*/vocals.wav (raw_peace starts @62s ep02, raw_protect @1068 ep05, raw_cantdie @1406 ep05,
  raw_beautiful @1174 ep12, raw_always @16 ep02, raw_land @676 ep01)

## Shots — EP01 (opening 0:07-1:20 has credits text; ED/OP credits 21:44-22:46 avoid)
Other-world battle (purple/blue/gold): 52 giant skeleton hand(1:30,3.8s) | 53 blue circles | 61,62 green circle | 66 skull in purple (1:54)
| 68 Shagrua CU (1:59) | 71 yellow circle | 92 lantern | 100,103,104 blue circles | 115-117 yellow blast | 130 purple sphere (3:04,3.9s)
| 135 glowing knight | 136 purple lightning | 139 blue circle | 140,144 blue beam | 141,149 blue dragon | 151,154 Shagrua in blue light
| 176-178 golden fire figure (4:09) | 179,180 skull spider | 181 blue rings | 186-188 blue x-ray skeleton | 195 purple EVIL EYE CU (4:37,4.6s)
| 199 eye ECU | 220 eye glow (5:37) | 221 magenta skull demon (5:39,3.2s) | 222 skull CU | 224 blue souls (5:49,7s)
| 202-210 flashback: flag, clouds, child at jail window(209), mansion(210) | 227 skeleton army | 233,234 fire slash | 237 silhouettes in flames (6:21)
| 254,256,258 skull explosion | 271 yellow explosion | 279 skull speaks "playthings" (7:04) | 292 rainbow skull burst (7:39,6s) | 293 magenta burst (7:45)
| 295 red/white circles (7:50,4s) | 304-308 Shagrua purple flames | 316 gold pentagram circle (8:14) | 318 gold blast | 320 lightning
| 321 Shagrua gold slash (8:19,2.5s) | 322,323 rainbow blast | 324 skull blue-white | 326 Shagrua scream CU (8:26) | 327,328 magenta burst
| 332 sword hits skull | 333 blue dome (8:34) | 335 white explosion (8:36,5s) | 347 gold circles reincarnation (8:50,2.2s) | 351 white light (8:56,6.9s)
Shinjuku arrival: 359 bloody neck | 361 Polka CU (9:54) | 362 street (9:56,4s) | 364 Cocoon Tower skyscraper (10:05,3.5s) "mountain high"
| 376 looks at hands (10:50) | 384 Shinjuku stn | 388 little girl smiling (11:18,4.5s) | 389 Polka CU "this land is peaceful" (11:22,4.7s)
| 391 eye CU | 392 blue backlit back silhouette (11:28,5.3s) | 393 sepia child spirits | 476 Cocoon tower (15:32)
Misaki: 411 smiling (12:40) | 433,434,437 creepy/glitch laugh (13:37-13:44) | 447 hugs Polka (14:05) | 458 purple red-eyes (14:43,3.6s)
| 464-466 knife slash blue trail (14:53) | 481,483 knives backlit/glint (15:54-15:58) | 501 blood petals (16:19) | 528 laughing w/ bloody knife (17:09,3.1s)
| 549,552 magenta CU (18:48,18:59) | 562 white flash red eyes
Polka/Corpse God: 479 shadowed face one glowing eye (15:48,4.3s) | 506-511 falling in white light | 516 blue child spirits (16:43)
| 540 eye ECU (18:06,4.8s) | 542 red backlit (18:14) | 543 spirit silhouettes on red (18:19,5s) | 545 purple ghost crowd (18:27)
| 554 hand out glowing eyes CASTING (19:02,6.2s) | 555 blue-lit hand out side (19:08,7s) | 556 blue rune flash | 559-561 magenta skeleton hand
| 563 skeleton hand grab | 564 blue circle from bone hand (19:22) | 574 gold-pink reincarnation circle (19:55,4.2s) | 575 Shagrua bloody pink eye (19:59,7s)
| 585,586,588 hand w/ purple tendrils (20:53-21:01) | 587 purple/red necromancy circle (20:57,4.5s) | 590 sunny Shinjuku skyline (21:05) "a peaceful life"
| 593 Polka glowing eyes hero CU (21:15,2.2s) | 594 pink skull demon true form (21:17,6.8s) | 597,598 red/pink skull burst (21:30)
| 660-664 sketch eye opening (22:46) | 667 official EN logo "DEAD MOUNT DEATH PLAY" (22:51,2.5s)
| 670 overhead blue circles w/ Misaki (23:00) | 672 Polka casting blue circles (23:05,3s) | 674 Polka CU glowing eyes blue circle HERO (23:12,2.5s) | 676 Misaki rising

## Shots — EP02 (OP 3:26-5:01 mostly has credits; sketch-eye->EN logo 4:54-5:01 is clean)
Monologue storybook (white/sepia, matches OPEN dialogue): 1 child silhouette alone in white vignette (0:03,6s) ** | 2 dark hands reaching (0:09)
| 3 hooded figure w/ red-eyed spiders (0:12) | 5 hooded skull profile (0:21) | 6 hooded figure on battlefield (0:24) | 9 sepia tunnel (0:34)
| 10 hooded skull + child (0:38,9.4s) | 16 kids playing w/ hooded figure (1:04) | 17 kids at table w/ hooded figure (1:07,2.5s) = "All I wanted was peace"
| 18 hooded figure standing w/ kids (1:09) = "Nothing more" | 20 skull mask (1:13) | 22 red X swords (1:24) | 24 red battlefield fire (1:31,4s)
| 30 skull silhouette on red (1:49) | 32 many red eyes in dark (1:56) | 36 skeleton on throne sepia (2:21,6.3s) | 37 armored legs arrive (2:28)
| 92 red eye ECU (4:29) | 117 pink magic circle (4:50) | 119-123 sketch eye opens/closes (4:54) | 126 EN logo (4:59,2.5s)
## Shots — EP12
11 Polka red eyes dark (1:16) | 37 Polka CU OP (1:54) | 52-54 red burst bgs (2:14) | 61 red eye ECU (2:31) | 86-90 sketch eye | 93 EN logo (3:01,2.5s)
| 105 Solitaire hand red glow (3:59) | 154-160 blue lightning hooded figure (7:25-7:34) ** | 182 pink skull demon true form (9:10,5.4s) **
| 183 blue silhouettes w/ spirits on white (9:15,3.8s) | 191 blue chained circle w/ eyes (9:52) | 192 Polka w/ purple circles (9:54,3.6s)
| 223 red spirit silhouettes (12:13) | 224 kids w/ tall figure (12:17) | 225 blue swirl magic (12:20,7.4s) | 230 big blue circle (12:32)
| 231,232 purple lightning | 243,244 purple lightning tendrils (13:35) | 245 pink EYE ECU (13:42,3s) ** | 246 blue circle array + lightning (13:45,9.7s) **
| 248 circle burst (14:02) | 273 dark figure pink eyes (15:53,6s) | 274 hand on blue magic circle (15:59,8.8s) ** | 291 many blue circles w/ Polka (17:18,13.7s) **
| 292 blue energy sphere burst (17:32,4s) ** | 307 blue circle purple lightning (18:24,4.5s) | 313 Polka face half-skull purple (18:44,9.2s) ***
| 316 blue circles (19:14) | 317-319 giant spectral hands/arms (19:17-19:31) ** | 322 spectral burst (19:39) | 325 spectral arm night sky (19:43,4.7s)
| 328 Polka w/ huge blue circles HERO (19:49,4s) *** | 329 pink eye in dark (19:53) | 333 hand grabs balloon (20:04) | 343 Polka (20:31,6.7s)

## DECISIONS (after viewing strips)
- CLOSE line changed: "I can't go dying" is an old man (not Corpse God); "so very beautiful" is Solitaire (villain). CLOSE = E01 682.90-685.10 "It seems this land I've arrived in is peaceful." (Polka)
- E05 twins hug visual for MID line: ep05 src 1076-1080 (Polka in b/w hood hugging twins); 1090 = hood profile CU.
- dark-haired armored man w/ glowing pink eye (E01 #195,#220,#326,#308,#68) = Shagrua the Calamity Crusher (antagonist hero), NOT Corpse God.
- Output: 1920x1080 @60fps, ~37.3s. Renderer = python (OpenCV+PIL) piping to ffmpeg. Proxies only exist for ep01,02,03,10,11,12 (enough).
## STORYBOARD (B[i] = beat i from song_analysis.json)
A cold open 0-5.34: E02#1 child alone (src 3.6+) | E02#16 kids+hooded figure (64.7+) | E02#5 hooded skull reveal (22.0+). Dialogue OPEN from 0.30 (pauses tightened).
B title 5.34-7.27: footage-in-text "DEAD MOUNT / DEATH PLAY" filled w/ E01#594 pink skull demon (1279.5+), zoom THROUGH letters into full frame.
C verse 7.27-15.33 (battle): #594 cont. | E01#68 Shagrua sword (120.6) | MOUNTAIN: E01#98 skeleton giant zoom (154.2) | #103 rings (159.6), #136 lightning (195.3)
  | VALLEY: E01#227 skeleton lord over army (368.4) | #176 gold figure (249.7), #144 beam (208.9) | RIVER: E01#141 blue dragon (203.8)
  | ENOUGH: #326 Shagrua scream (506.2) -> #321 gold slash (499.5) | #332 sword strike (513.0) -> #335 light pillar white-out (517.5)
D 15.33-21.8: #335 white | #347 reincarnation circle (530.6) | #361 Polka CU (594) | #364 Cocoon tower (606) | #362 street (596.5)
  | split-screen two worlds (E01#237 flames 381.3 | E01#590 skyline 1265.6) "no matter how far" | #392 blue backlit silhouette (691.8)
E 21.8-28.31: #393 sepia kids (694.2) | #411 Misaki smile (760.1) | #528 Misaki laugh knife (1029.5) | #501 Misaki lunge (979.4)
  | #540 eye ignites (1088.3) | #554 hand tendrils (1145.5) | #555 circle forms (1148.9) + #556 rune flash (1155.9)
E8 28.31-30.12 (music muffled, MID line @28.22): E05 twins hug (1076.3) | E12#313 half-skull face (1126)
F chorus 30.12-33.37: E12#328 hero circles (1189.5) | E12#292 sphere burst (1054.5) | E12#318 spectral hands (1169.5) | E01#594/E12#182 skull demon
  | E01#292 rainbow burst (459.2) | E12#248 burst (842.4)/E01#598 (1290.5) | E01#674 Polka hero CU (1392.7)
G outro 33.37-37.3: E01#590 skyline (CLOSE line @33.6) | E01#389 Polka closes eyes (683.5) | end title on black.

# ===================== V2 (user feedback 2026-11-18) =====================
User liked concept. Wants: more creative fonts + better placement, "border tricks" + other cinematic tricks, better use of scenes,
SOUND EFFECTS for a movie feel ("a little cinematic but still an edit"). Keep song, story, 3 dialogue lines.
## Reference analysis (dense sheets in ref/r_*.jpg)
- MARATHON (same song!): footage shrunk into a TILTED 3D thin-bordered frame (double line border, corner ticks, + markers on black),
  elegant thin serif caps lyrics in yellow OVERLAPPING the frame's bottom edge ("AIN'T NO MOUNTAIN / HIGH / VALLEY / LOW / RIVER / WIIIIDE / ENOUGH, BABY");
  techno title + katakana alt title; dialogue big serif lower-left word by word. -> this is what user means by "border tricks".
- JPOXI: every lyric word on screen, 3D-perspective tilted bold italic, colour matched to scene, text BEHIND characters, glow.
- VRENS: stacked bold condensed italic lines building up, red highlight words, cut-out characters on paper bg, title cards.
- Aidour (mixed): pure motion flow/match cuts, no static shots. Vinland: big serif cut off at edges + script word, glass strips, HUD glyphs.
## V2 tools verified
- Character mattes: rembg `isnet-anime` (0.7s/frame). WORKS: Shagrua sword (E01 121.6), Polka hero CU (E01 1393.5), Misaki smile (761.2),
  Misaki laugh (1030.2), twins hug (E05 1077.5), Polka speaks (E01 683.5), half-skull (E12 1127). FAILS: scream, tiny figure in circles, extreme CU, dark hand, skeleton.
- SFX: Mixkit free library, 113 files in sfx/<id>.wav, measured in sfx/analysis.json (on/peak/end seconds, LUFS). catalog: sfx_src/catalog.json.
  (assets.mixkit.co/active_storage/sfx/<id>/<id>.wav ; listing pages need browser headers)
- Fonts added in fonts/: InstrumentSerif(+Italic), Fraunces(+Italic var), GrenzeGotisch(var), UnifrakturCook, PirataOne, IMFell(+Italic), MrDafoe,
  PermanentMarker, RockSalt, ReenieBeanie, DelaGothicOne(JP), ZenAntique(JP), ShipporiMinchoB1(JP), YujiSyuku(JP), BodoniModa(+Italic), AbrilFatface,
  Shrikhand, RubikWetPaint, Yellowtail, Monoton, BigShoulders.
## V2 plan (sections keep v1 timing)
A cold open = old FILM REEL frame (sprockets, flicker, scratches), dialogue as INK text inside the storybook picture, kanji 平穏.
B title zoom-through kept + frame lines, micro text, katakana, SFX hit/riser.
C verse = footage alternates FULL <-> floating 3D bordered CARD; MOUNTAIN/VALLEY/RIVER overlap/behind the card; text behind Shagrua; ENOUGH blackletter.
D reincarnation -> Shinjuku location card 新宿; "how far" = two cards drifting apart in depth.
E "just call my name" = POLAROID stack with handwritten names (kids, Misaki, Takumi, me) + shutter SFX; punch through Polka's photo into eye-ignite action.
P pocket = intimate card, heartbeat SFX, "I'll protect you, / no matter what." (blackletter).
F chorus = full-frame, 3D/extruded word slams, ENOUGH behind Polka (matte).
G outro = Polka speaks, "peaceful." big; end lockup with red hanko seal 屍神殿 + church bell.
## V2 build state
- Files: tl2.py (timeline), r2core.py (engine: 3D planes, mattes, text layers), render2.py (scenes), audio2.py (mix + SFX), prep2.py (clips + mattes).
- Run: python prep2.py ; python audio2.py ; python render2.py final ; mux out/final2_video.mp4 + out/mix2.wav. Debug frames: TS=1.0,9.4 OUT=out/x.jpg python dbg2.py
- SFX balance: per-sound loudness target + peak cap (lv+10.5 dB) + bus trim -2 dB; verified RMS per section (sfx ~2-5 dB under music, equal at title/chorus).
- Known design choices: ENOUGH (chorus) sits in FRONT lower third (Polka's head fills frame); "peaceful." is behind Polka via matte; END=39.3s.

# ===================== V3 (user feedback 2026-11-18 #2) =====================
User: "I see what you doing — just keep the ORIGINAL Dead Mount Death Play logo, and include the Lemmings fight with Corpse God in the café scenes."
=> (1) replace my custom title + custom end lockup/seal with the OFFICIAL logo footage; (2) add the E05 bar (Clarissa's) fight vs Lemmings.
## Official logo footage (E01)
- EN logo build: 1368.0-1369.8 sketch eye closing on WHITE | 1370.0 black w/ white hair lines | ~1370.6 "DEAD" appears | ~1371.2 "DEATH" + skull art
  | ~1372.0 full stacked logo "DEAD / MOUNT / DEATH PLAY" (black/white bars) holds to ~1373.3. (same build also E02 4:54-5:01, E12 2:56-3:03)
- JP title card: 1293.0 dark blue typing "DEAD MOUNT.." | 1294.6 glitch burst | 1296.0 JP logo デッドマウント・デスプレイ on WHITE (with small EN name)
  | 1297.5 glitching blue over skyline | 1299.0 blue logo over Shinjuku skyline | 1300.5 skyline only.
## E05 café/bar fight vs Lemmings (dark scene; sheets/dark_e05a.jpg, dark_e05b.jpg; times mm:ss.s in ep05; OP = 2:50-4:20 skip; chibi cutaways skip)
Setup: 0:40.5(7.9s) Misaki+Polka two-shot | 0:48.4,0:49.3 Polka pink EYE ECU ignite | 0:50.9-0:52.1 PURPLE ghost swirl (fast) + 0:52.1(3.8s) ghost mass
 | 0:55.8 Polka profile pink eye
Lemmings vs cops: 0:59.4 leap (m8) | 1:04.8 Lemmings hooded hand reach (m6) | 1:05.6 cloak sweep | 1:10.9 bandaged face w/ victim | 1:15.7 bandaged face CU
 | 1:18.8(2.0s) Lemmings bandaged face ECU glowing ** | 1:30.8 arm strike (m8) | 1:31.6(1.0s) bandaged fist catches blow ** | 1:40.1 Lemmings from behind
 | 1:42.1 Polka pink eyes (m8) | 1:53.2 Polka lunges reaching (m7), 1:53.6 hand, 1:54.1 open hand CU | 1:54.7(5s) Polka blue-lit profile gritting teeth, 2:00.6 CU
 | 2:04.3 handcuffs | 2:05.3 fight (m10) | 2:07.8 purple skull flash (m24) | 2:08.9 purple spirits | 2:10.1 Polka eye
 | 2:11.4(2.2s)+2:17.9(4s) Corpse God skull true form blue-white w/ Polka ** | 2:35.5-2:37.5 skeletal hand + blue runes/circles (fast)
 | 2:44.8(5.5s) Polka casting, blue circle arrays, glowing eyes *** (best ~2:46.5-2:50.2)
After OP (avoid 4:20-4:25: episode-title text): 4:28.5 blue circle + skeletal arm sweep (m14) | 4:32.1(3.8s) Polka reaching w/ blue circle + bone hand **
 | 4:35.9 Polka pink eyes | 4:46.0 skeleton hanging from lamp | 4:52.2 Polka w/ pendant | 4:54.9 circles on walls | 4:56.4 Polka hand out pink eyes **
 | 4:57.6(1.8s,m9) big BLUE CIRCLE burst *** | 4:59.2(1.4s) skeletal hand reaching ** | 5:00.7-5:06.5 bone blades vs Lemmings, rapid (m5-m12) **
 | 5:07.9 Lemmings dodge | 5:08.6 bones sweeping (m10) ** | 5:09.4 bone blades | 5:14.6 Misaki shocked CU | 5:22.2 Lemmings bandaged grin CU *
 | 5:23.4 Polka shouting pink eyes ** | 5:24.6 Misaki glasses ECU | 5:27.0 Misaki held by Lemmings | 5:33.7 Polka pink eyes CU
 | 5:41.2(0.8s,m11) Lemmings hooded silhouette w/ PURPLE ghosts *** | 5:42.2 Polka pink eyes front ** | 6:06.1 Misaki glasses glint ECU | 6:07.1 fork
 | 6:10.6(3.4s) Lemmings face w/ fork | 6:14.0 Misaki grin
Finale spell: 6:26.2 blue circles | 6:28.8(2.0s) Polka pink eyes ECU *** | 6:29.9 purple vein flash (m19) | 6:31.1(2.1s) purple ghost mass ** | 6:32.5 teal streak
 | 6:34.7(1.8s)+6:36.1 blue-white energy burst *** | 6:36.8(3.5s) MANY blue circles array *** | 6:41.0(2.0s,m13) furniture/debris flying blue ***
 | 6:42.8-6:45 white energy burst / white-out *** | 6:45.7(3.2s) Polka standing in blue light ** | 6:48.4-6:51 bar wide, debris + giant skull forming ***
 | 6:52.4(2.4s) giant SKULL face *** | 6:54.0(0.8s) skull RED EYES *** | 6:55.0(1.2s,m11) skeletal monster lunges *** | 6:56.2 Lemmings among bones
## V3 logo timing (frame-accurate, E01)
- EN build: hair-lines flicker 1369.97-1370.43 | "DEAD" 1370.47 | "MOUNT" (white) 1370.84 | "DEATH"+skull 1371.22 | FULL stacked logo 1371.47 -> holds to ~1373.9
  -> output: DEAD@5.86, MOUNT@6.32, DEATH@6.78, FULL@7.27 hold to 8.22 (all on beats). No custom title text.
- JP card: typing on dark blue 1292.2-1294.45 | glitch 1294.49-1294.70 | JP logo on WHITE clean 1294.70-1297.21 | static 1297.25-1297.46
  | blue logo glitching over skyline 1297.50-1299.8 | skyline only 1299.96-1300.96 (then unrelated at 1301.0)
  -> ending plays this REVERSED: skyline (with "peaceful.") -> logo glitches in -> static -> logo on white hold -> black.
- E04 Lemmings reveal: 22:01.3 (1321.3s, 4.0s static) bandaged hooded face, blue — clean until credits start 22:07. Also 21:41.5 glowing eye in dark; 21:53.7 hooded.
## V3 plan
- B title = official EN build. End = official JP card reversed (replaces G2 + custom lockup + seal).
- E-action 25.80-28.55 = café threat: Lemmings reveal -> strike -> grabs Misaki/grin -> Polka shouts -> Polka reaches -> blue circle burst.
- Pocket P2 = Polka pink-eyes ECU (E05 6:28.8) instead of E12 half-skull. P1 twins hug stays.
- Chorus 30.50-33.6 = café finale: energy burst -> circles array -> debris flying -> white burst -> giant skull -> red eyes -> skeletal monster lunge (final word).
## V3 build state (delivered: out/DMDP_edit_v3_1080p60.mp4, MASTER alongside)
- Same files as V2 (tl2.py / r2core.py / render2.py / audio2.py / prep2.py); V2 originals kept as *_v2.bak in scratchpad and in git history.
- Title = scene_logo(): official EN build from E01 1370.48, steps auto-detected in the clip, mapped to beats 5.86/6.32/6.78/7.27, hold to 8.22. No glow/vignette/aberration on logo.
- End = end_logo_frame(): E01 1295.9+ played backwards via END_MAP (skyline -> logo glitch-in 36.85 -> static 37.45 -> JP logo on white 37.55 -> fade 39.0-39.3).
- Cafe fight: L1-L6 (25.80-28.55), P1/P2 pocket, F1-F6 chorus all from E04 end / E05 bar. Grades "bar"/"bar_hi" brighten the dark bar footage.
- Only cafe matte that works: F6 (Polka in blue light) -> final chorus word split in two halves either side of his head, behind him.
- Too dark to use even graded: E05 strike 1:30.8, skeletal lunge 6:55, Polka hand-out 4:56, bone hand 4:59.

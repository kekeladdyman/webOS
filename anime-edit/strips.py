"""Filmstrips for candidate shots. usage: strips.py name ep:id,id,... ep:id,..."""
import sys, json, os, cv2, numpy as np
root=os.path.dirname(os.path.abspath(__file__))
name=sys.argv[1]; items=[]
for arg in sys.argv[2:]:
    ep,ids=arg.split(":")
    d={s["i"]:s for s in json.load(open(f"{root}/shots/ep{ep}.json"))["shots"]}
    items+=[(ep,d[int(i)]) for i in ids.split(",")]
N,TW,TH,LW=8,120,68,96
per=16; caps={}
for p in range(0,len(items),per):
    chunk=items[p:p+per]; img=np.zeros((len(chunk)*(TH+2),LW+N*TW,3),np.uint8)
    for r,(ep,s) in enumerate(chunk):
        if ep not in caps: caps[ep]=cv2.VideoCapture(f"{root}/proxy/ep{ep}.mp4")
        cap=caps[ep]; y=r*(TH+2)
        cv2.putText(img,f"E{ep} #{s['i']}",(2,y+16),cv2.FONT_HERSHEY_SIMPLEX,0.42,(255,255,255),1,cv2.LINE_AA)
        cv2.putText(img,f"{s['t0']:.1f}s",(2,y+34),cv2.FONT_HERSHEY_SIMPLEX,0.4,(160,255,160),1,cv2.LINE_AA)
        cv2.putText(img,f"d{s['dur']:.1f} m{s['mot']:.0f}",(2,y+52),cv2.FONT_HERSHEY_SIMPLEX,0.38,(160,200,255),1,cv2.LINE_AA)
        for k in range(N):
            f=int(s["f0"]+ (k+0.5)/N*(s["f1"]-s["f0"]))
            cap.set(cv2.CAP_PROP_POS_FRAMES,f); ok,fr=cap.read()
            if ok: img[y:y+TH,LW+k*TW:LW+(k+1)*TW]=cv2.resize(fr,(TW,TH),interpolation=cv2.INTER_AREA)
    out=f"{root}/sheets/strip_{name}_{p//per:02d}.jpg"; cv2.imwrite(out,img,[cv2.IMWRITE_JPEG_QUALITY,82]); print(out,len(chunk))

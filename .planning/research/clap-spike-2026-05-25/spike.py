"""CLAP Phase-A viability spike — audio->audio + text->audio similarity on real tracks.
/tmp-only. Does NOT touch the repo or ~/.cache/vibemix.
"""
from __future__ import annotations
import os, sys, time, glob, json
import numpy as np

MUSIC_DIR = "/Users/ozai/Music/runnin over my body"

# Hand-picked cross-genre set: hard-techno/aggressive vs vocal/funk/pop.
# Names matched loosely against the folder; we resolve actual paths below.
WANT = [
    # likely hard / aggressive electronic / techno-ish
    "Brutalismus 3000 - badthiings",
    "Brutalismus 3000 - nur mein",
    "CRRDR & FREEBOT - TRI-TEK",
    "2HOT2PLAY",            # hardstyle/hard label HOTMEAL
    "Reversed Worrier",
    "64 (Extended Mix)",
    "2AT x Nixss - Nonstop",
    # likely vocal / pop / funk / rap
    "Azealia Banks - Competition",
    "Azealia Banks - Liquorice",
    "365 featuring shygirl",
    "Charli XCX - Guess",
    "Club classics",
    "BDE (feat. slowthai)",
    "As Long As",
    "BOY CRAZY",
]

def resolve_paths():
    allf = glob.glob(os.path.join(MUSIC_DIR, "*.mp3"))
    picks = []
    for w in WANT:
        for f in allf:
            base = os.path.basename(f)
            if w.lower() in base.lower():
                picks.append(f)
                break
    # dedup keep order
    seen=set(); out=[]
    for p in picks:
        if p not in seen:
            seen.add(p); out.append(p)
    return out

def main():
    import librosa
    from transformers import ClapModel, ClapProcessor
    import torch
    torch.set_num_threads(max(1, os.cpu_count() or 4))

    files = resolve_paths()
    print(f"[setup] resolved {len(files)} files")
    for f in files:
        print("  -", os.path.basename(f))
    if len(files) < 8:
        print("WARN: too few files resolved")

    t0=time.time()
    model = ClapModel.from_pretrained("laion/larger_clap_music")
    processor = ClapProcessor.from_pretrained("laion/larger_clap_music")
    model.eval()
    print(f"[load] model+processor loaded in {time.time()-t0:.1f}s")

    SR = 48000
    names=[]; vecs=[]; embed_times=[]
    for f in files:
        try:
            te=time.time()
            # load a 30s mono excerpt from ~20s in (skip intro silence)
            y, _ = librosa.load(f, sr=SR, mono=True, offset=20.0, duration=30.0)
            if y.size < SR*5:  # too short -> load from start
                y, _ = librosa.load(f, sr=SR, mono=True, duration=30.0)
            inp = processor(audio=y, sampling_rate=SR, return_tensors="pt")
            with torch.no_grad():
                emb = model.get_audio_features(**inp)
            # transformers 5.9: get_audio_features returns BaseModelOutputWithPooling;
            # the projected joint-space (512-d) embedding is .pooler_output.
            emb = getattr(emb, "pooler_output", emb)
            v = emb.squeeze(0).cpu().numpy().astype(np.float32)
            vecs.append(v); names.append(os.path.basename(f))
            dt=time.time()-te; embed_times.append(dt)
            print(f"[embed] {dt:5.2f}s  {os.path.basename(f)[:55]}")
        except Exception as e:
            print(f"[embed-ERR] {os.path.basename(f)}: {e!r}")

    X = np.vstack(vecs)
    print(f"\n[stats] embedded {len(names)} tracks, dim={X.shape[1]}, "
          f"median embed {np.median(embed_times):.2f}s, mean {np.mean(embed_times):.2f}s")

    def l2(M):
        return M / (np.linalg.norm(M, axis=1, keepdims=True)+1e-9)

    # ---- raw cosine (no centering) ----
    Xn = l2(X)
    S = Xn @ Xn.T
    # ---- mean-centered cosine ----
    Xc = X - X.mean(axis=0, keepdims=True)
    Xcn = l2(Xc)
    Sc = Xcn @ Xcn.T

    off = S[~np.eye(len(S),dtype=bool)]
    offc = Sc[~np.eye(len(Sc),dtype=bool)]
    print(f"[raw cosine] off-diag mean={off.mean():.3f} std={off.std():.3f} min={off.min():.3f} max={off.max():.3f}")
    print(f"[centered ]  off-diag mean={offc.mean():.3f} std={offc.std():.3f} min={offc.min():.3f} max={offc.max():.3f}")

    def topk(M, i, k=5):
        order = np.argsort(-M[i])
        out=[]
        for j in order:
            if j==i: continue
            out.append((names[j], float(M[i,j])))
            if len(out)>=k: break
        return out

    # seed tracks: pick a couple of hard ones + a couple vocal ones if present
    def find_idx(sub):
        for i,n in enumerate(names):
            if sub.lower() in n.lower(): return i
        return None
    seeds = []
    for sub in ["Brutalismus 3000 - badthiings","CRRDR","TRI-TEK","2HOT2PLAY","Azealia Banks - Competition","Charli XCX","365 featuring"]:
        i=find_idx(sub)
        if i is not None and i not in seeds: seeds.append(i)
    seeds=seeds[:4]

    print("\n================ RAW COSINE neighbors ================")
    for i in seeds:
        print(f"\nSEED: {names[i]}")
        for n,s in topk(S,i): print(f"   {s:+.3f}  {n}")
    print("\n================ MEAN-CENTERED neighbors ================")
    for i in seeds:
        print(f"\nSEED: {names[i]}")
        for n,s in topk(Sc,i): print(f"   {s:+.3f}  {n}")

    # ---- text -> audio ----
    print("\n================ TEXT -> AUDIO ================")
    queries = ["hard aggressive techno", "soft female vocal pop song", "funky house groove", "distorted hardcore gabber"]
    txt = processor(text=queries, return_tensors="pt", padding=True)
    with torch.no_grad():
        _t = model.get_text_features(**txt)
        temb = getattr(_t, "pooler_output", _t).cpu().numpy().astype(np.float32)
    Tn = l2(temb)
    TS = Tn @ Xn.T   # query x track
    for qi,q in enumerate(queries):
        order=np.argsort(-TS[qi])[:5]
        print(f"\nQUERY: '{q}'")
        for j in order:
            print(f"   {TS[qi,j]:+.3f}  {names[j]}")

    # dump raw for record
    with open("/tmp/clap_spike/raw_results.json","w") as fh:
        json.dump({"names":names,"embed_times":embed_times,
                   "raw_offdiag":[off.mean(),off.std(),off.min(),off.max()],
                   "centered_offdiag":[offc.mean(),offc.std(),offc.min(),offc.max()]}, fh, indent=2, default=float)
    print("\n[done]")

if __name__=="__main__":
    main()

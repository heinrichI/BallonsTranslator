import cv2,glob,os
for p in sorted(glob.glob("debug_dump/*mask*.png")):
    img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(p, "cannot read")
        continue
    cnt = int((img>0).sum())
    h,w = img.shape
    print(os.path.basename(p), "nonzero=", cnt, "area=", h*w)
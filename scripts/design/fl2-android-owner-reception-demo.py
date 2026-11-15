#!/usr/bin/env python3
"""Native Android DEMO OWNER/RECEPTION smoke via real UIAutomator.
No live hotel credentials, real reservations, or physical device claims.
"""
import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

APP="kg.go.ms.staff"
OUT=Path("android-emulator-evidence")
OUT.mkdir(exist_ok=True)
records=[]

def adb(*args,check=True):
    p=subprocess.run(["adb",*args],text=True,capture_output=True,timeout=50)
    if check and p.returncode: raise RuntimeError(f"adb {args[0]} failed: {p.stderr[-700:]}")
    return p.stdout

def dump():
    # UIAutomator may momentarily fail while React Native changes screens.
    last=None
    for _ in range(8):
        try:
            adb("shell","uiautomator","dump","/sdcard/marina-qa.xml")
            xml=adb("exec-out","cat","/sdcard/marina-qa.xml")
            if xml.strip().startswith("<?xml"):
                return ET.fromstring(xml)
        except Exception as exc:
            last=exc
        time.sleep(1.5)
    raise AssertionError(f"Android hierarchy not accessible: {last}")

def nodes(root):
    return [
      {"label":(e.attrib.get("content-desc") or e.attrib.get("text") or "").strip(),
       "text":e.attrib.get("text","").strip(),
       "bounds":e.attrib.get("bounds",""),
       "clickable":e.attrib.get("clickable")=="true"}
      for e in root.iter("node")
    ]

def labels():
    return [x["label"] for x in nodes(dump()) if x["label"]]

def tap(label,exact=True):
    for _ in range(12):
        options=nodes(dump())
        matching=[x for x in options if (x["label"].casefold()==label.casefold() if exact else label.casefold() in x["label"].casefold()) and x["clickable"]]
        if not matching: matching=[x for x in options if (x["text"].casefold()==label.casefold() if exact else label.casefold() in x["text"].casefold())]
        if matching:
            area=matching[0]["bounds"]
            m=re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",area)
            assert m,area
            x1,y1,x2,y2=map(int,m.groups())
            adb("shell","input","tap",str((x1+x2)//2),str((y1+y2)//2))
            time.sleep(2)
            return
        time.sleep(1.5)
    raise AssertionError(f"Can't tap {label!r}; current labels: {labels()[:65]}")

def capture(name):
    shot=subprocess.run(["adb","exec-out","screencap","-p"],capture_output=True,timeout=25,check=True)
    assert len(shot.stdout)>3000
    (OUT/name).write_bytes(shot.stdout)

def await_labels(must_any,where,timeout=30):
    limit=time.time()+timeout
    last=[]
    while time.time()<limit:
        last=labels()
        if any(any(token.casefold() in label.casefold() for label in last) for token in must_any):
            return last
        time.sleep(1.5)
    raise AssertionError(f"{where} not visible; expected one of {must_any}, got {last[:60]}")

def run_role(role):
    # Force a clean synthetic store to start role selection; do not touch live data.
    adb("shell","pm","clear",APP)
    adb("shell","monkey","-p",APP,"-c","android.intent.category.LAUNCHER","1")
    await_labels(["Connect to a hotel","Подключить гостиницу","Отелге туташуу"],"Connect")
    tap(role)
    visible=await_labels(["DEMO","Demo mode","Overview","Reception","Обзор","Ресепшен","Главная"],role)
    assert not any("FATAL EXCEPTION" in x for x in visible)
    capture(role.lower()+"-demo-native.png")
    # Reach Settings/Profile via true Android UI, then actually log out.
    # A bottom tab may say "More" when Profile is not a primary tab.
    visible=labels()
    if any(x.casefold()=="more" for x in visible):
        tap("More")
    elif any(x.casefold()=="ещё" for x in visible):
        tap("Ещё")
    visible=labels()
    for option in ["Profile","Профиль","Мой профиль","Профил"]:
        if any(option.casefold()==x.casefold() for x in visible):
            tap(option);break
    else:
        # Some roles expose their profile as a primary tab.
        tap("Profile",exact=False)
    # Profile's logout is intentionally BELOW the fold on 320-430dp phones.
    # Native UIAutomator only exposes currently laid-out/visible nodes.
    # Scroll the actual Android ScrollView rather than accepting a web/mock result.
    logout_labels=["Sign out","Log out","Выйти","Чыгуу"]
    visible=labels()
    display=adb("shell","wm","size")
    size=re.search(r"(\d+)x(\d+)",display)
    assert size, f"Cannot determine native Android size: {display}"
    width,height=map(int,size.groups())
    for attempt in range(8):
        if any(any(option.casefold()==item.casefold() for item in visible) for option in logout_labels):
            break
        adb("shell","input","swipe",str(width//2),str(int(height*.75)),str(width//2),str(int(height*.28)),"380")
        time.sleep(1.3)
        visible=labels()
    else:
        capture(role.lower()+"-missing-signout.png")
        raise AssertionError(f"Native Profile logout remains unreachable after 8 real swipes: {visible[-45:]}")
    for option in logout_labels:
        if any(option.casefold()==x.casefold() for x in visible):
            tap(option);break
    await_labels(["Connect to a hotel","Connect","Sign in","Войти"],"Signed-out screen")
    capture(role.lower()+"-signed-out.png")
    records.append({"role":role,"native_demo_login":True,"native_logout":True,"synthetic_data_only":True})

for role in ("Owner","Reception"):
    run_role(role)

(OUT/"native-role-results.json").write_text(json.dumps({"physical_device":False,"live_auth":False,"real_booking":False,"roles":records},indent=2))
print("MARINA_NATIVE_ANDROID_OWNER_RECEPTION_DEMO_LOGIN_LOGOUT_PASS")

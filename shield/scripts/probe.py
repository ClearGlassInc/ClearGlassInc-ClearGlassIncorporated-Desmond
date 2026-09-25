#!/usr/bin/env python3
import socket,sys,struct
mode=sys.argv[1]
if mode=="http":
    s=socket.create_connection(("10.77.0.1",8080),timeout=2)
    s.sendall(b"GET / HTTP/1.0\r\nHost: service.shield.test\r\n\r\n")
    data=s.recv(2048); s.close()
    if b"200" not in data: raise SystemExit("synthetic HTTP probe failed")
elif mode=="dns":
    qid=0x1234
    qname=b"".join(bytes([len(x)])+x for x in b"service.shield.test".split(b"."))+b"\0"
    packet=struct.pack("!HHHHHH",qid,0x0100,1,0,0,0)+qname+struct.pack("!HH",1,1)
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.settimeout(2)
    s.sendto(packet,("10.77.0.1",5353)); data,_=s.recvfrom(2048); s.close()
    if data[:2]!=struct.pack("!H",qid) or socket.inet_ntoa(data[-4:])!="10.77.0.1":
        raise SystemExit("synthetic DNS probe failed")
elif mode=="blocked":
    try:
        s=socket.create_connection(("10.77.0.1",8080),timeout=1); s.close()
    except OSError:
        pass
    else:
        raise SystemExit("protected test route unexpectedly reachable")
else:
    raise SystemExit("unknown probe")

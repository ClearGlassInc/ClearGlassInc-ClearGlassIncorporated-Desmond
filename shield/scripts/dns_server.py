#!/usr/bin/env python3
"""Test-only resolver for three synthetic records under shield.test.

service.shield.test and health.shield.test answer with the gateway's tunnel
address. blocked.shield.test, and any other name, is NXDOMAIN.
Usage: dns_server.py [host] [port]
"""
import socket
import struct
import sys

HOST=sys.argv[1] if len(sys.argv)>1 else "10.77.0.1"
PORT=int(sys.argv[2]) if len(sys.argv)>2 else 5353
ANSWER_IP="10.77.0.1"
RECORDS={b"service.shield.test",b"health.shield.test"}
sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
sock.bind((HOST,PORT))
while True:
    data,addr=sock.recvfrom(4096)
    if len(data)<12:
        continue
    tid=data[:2]
    qdcount=struct.unpack("!H",data[4:6])[0]
    if qdcount != 1:
        continue
    offset=12
    labels=[]
    while offset < len(data) and data[offset]:
        n=data[offset]
        offset+=1
        labels.append(data[offset:offset+n])
        offset+=n
    if offset >= len(data):
        continue
    offset+=1
    if offset+4>len(data):
        continue
    qtype,qclass=struct.unpack("!HH",data[offset:offset+4])
    question=data[12:offset+4]
    name=b".".join(labels).lower()
    answers=b""
    rcode=3
    if name in RECORDS:
        rcode=0
        if qtype==1 and qclass==1:
            answers=b"\xc0\x0c"+struct.pack("!HHIH4s",1,1,30,4,socket.inet_aton(ANSWER_IP))
    header=tid+struct.pack("!HHHHH",0x8180|rcode,qdcount,1 if answers else 0,0,0)
    sock.sendto(header+question+answers,addr)

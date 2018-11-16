import dpkt
import struct
import socket
import os
from dpkt.compat import compat_ord

QEM_SOF = 128 << 24
QEM_EOF = (64 << 24) + 7


def mac_addr(address):
    """Convert a MAC address to a readable/printable string

       Args:
           address (str): a MAC address in hex form (e.g. '\x01\x02\x03\x04\x05\x06')
       Returns:
           str: Printable/readable MAC address
    """
    return ':'.join('%02x' % compat_ord(b) for b in address)

def inet_to_string(inet):
    """Convert inet object to a string

        Args:
            inet (inet struct): inet network address
        Returns:
            str: Printable/readable IP address
    """
    # First try ipv4 and then ipv6
    try:
        return socket.inet_ntop(socket.AF_INET, inet)
    except ValueError:
        return socket.inet_ntop(socket.AF_INET6, inet)

f = open("/scratch/qem/data.pcap")

# Initialise the packet capture file reader
pcap = dpkt.pcap.Reader(f)

f_write= open("header_data.pcap", "w")
pcap_writer = dpkt.pcap.Writer(f_write)

for timestamp, buffer in pcap:
    
    ethernet_layer = dpkt.ethernet.Ethernet(buffer)

    ip_layer = ethernet_layer.data
    udp_layer = ip_layer.data

    #print ethernet_layer
    #print type(ethernet_layer)
    #print "Ethernet Layer: ", mac_addr(ethernet_layer.src), mac_addr(ethernet_layer.dst), ethernet_layer.type
    #print "IP Layer ",  inet_to_string(ip_layer.src), inet_to_string(ip_layer.dst) 
    #print "UDP Layer ", udp_layer.sport, udp_layer.dport, len(udp_layer.data)
    
    data_length = len(udp_layer.data)
    raw_trailer = udp_layer.data[data_length-8:]
    #print type(udp_layer.data[data_length-8:])

    frame_number, packet_number = struct.unpack("<II", udp_layer.data[data_length-8:])
    trailer = struct.unpack("<II", udp_layer.data[data_length-8:])

    if packet_number == QEM_SOF:
        print "------- Start Of Frame -------"
        print frame_number, packet_number - QEM_SOF

    elif packet_number == QEM_EOF:
        print frame_number, ((packet_number - QEM_EOF) + 7)
        print "------- End Of Frame -------"
    else:
        print frame_number, packet_number

    stripped_udp_packet = udp_layer.data[:data_length-8]
    print len(stripped_udp_packet)
    header  = struct.pack("<II", frame_number, packet_number)
    print len(header)
    #print header, raw_trailer
    
    udp_packet = header + stripped_udp_packet
    print len(udp_packet)
    pcap_writer.writepkt(udp_packet)

 


    
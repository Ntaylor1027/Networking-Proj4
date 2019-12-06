#!/usr/bin/env python3
"""Usage: server_udp.py <outFile>

    Options:
        -h --help    

    Arguments:
        outFile             (String) Name of file to write to

"""
import socket
from docopt import docopt

def grab_seq_num(string):
    #string = string.decode('utf-8') # convert bytes to string
    payload = string.find(" ") + 1 # Find first space
    return (int(string[:payload]),string[payload:])

def iterate_variable(i):
    """
    Properly iterates variable to loop around window
    """
    if (i + 1) == len(window): # if we are at the end of our window
        return 0 # reset to beginning
    return i + 1 # iterate by 1
    

if __name__ == "__main__":
    args = docopt(__doc__)
    #print(args)
    
    outfile = open(args['<outFile>'], 'w') 

    # Setup Sliding window vars
    window = [str(i) for i in range(0,10)] # 10 buffer length
    ack_line = 0
    last_send = 9

    # Sequence validation
    expected_seq_num = 0

    # Grab socket details
    UDP_IP = socket.gethostbyname("10.0.0.2")
    UDP_PORT = 5432
    SEND_IP = socket.gethostbyname("10.0.0.1")

    # Set socket and listen
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    sock.bind((UDP_IP, UDP_PORT))
    #sock.listen(5)

    RESYNC_REQ = bytes("Resync", "utf-8")

    print(f"IP: {UDP_IP}\nPORT: {UDP_PORT}")
    
    # Listen for incoming packets
    i = 0
    while True:
        msg, address = sock.recvfrom(80)
        #print(f"Connection from {address}")
        #data, addr = sock.recvfrom(1024)
        #print(F"received message: {msg}")
        
        i+=1
        payload = msg.decode('utf-8')
        if len(payload) == 0: # didn't read anything
            continue

        if payload == "0xffff": # termination string
            break

        if payload == "Resync": # send current expected sequence number
            print(f"Resyncing... expected:{expected_seq_num} msg:{payload}")
            sock.sendto(bytes(f"RTR {expected_seq_num}", 'utf-8'), (SEND_IP, UDP_PORT))

        else:
            pyld_seq_num, pyld_msg = grab_seq_num(payload)
            print(f"i: {i} seq_num: {pyld_seq_num}, expected: {expected_seq_num} message: {pyld_msg}")

            if pyld_seq_num == expected_seq_num: # Correct sequenced packet arrived
                print(f"CHECK:: i: {i} seq_num: {pyld_seq_num}, expected: {expected_seq_num} message: {pyld_msg}")
                expected_seq_num = iterate_variable(expected_seq_num) # expect the next seq num
                ack_line = iterate_variable(ack_line) # Acknowlege it in the alg
                last_send = iterate_variable(last_send) # Move our glass door ending over 1
                outfile.write(pyld_msg)
                print(f"RTR {expected_seq_num}")
                # ACK seq num to client
                sock.sendto(bytes(f"RTR {expected_seq_num}", 'utf-8'), (SEND_IP, UDP_PORT))
            else: # Send current expected sequence number
                sock.sendto(bytes(f"RTR {expected_seq_num}", 'utf-8'), (SEND_IP, UDP_PORT))
outfile.close()
#!/usr/bin/env python3
"""Usage: client_udp.py <destIP> <inFile>

    Options:
        -h --help    

    Arguments:
        destIP             (String) IP(v4) address of Destination hardware
        inFile             (String) Name of file to read from

"""
import socket
import time
from docopt import docopt

window = [str(i) for i in range(0,10)] # 10 buffer length

def resync_index(send_index, message_index, rtr):
    while send_index != rtr:
        send_index = decrement_variable(send_index)
        message_index-=1
    return send_index, message_index

def iterate_variable(i):
    """
    Properly iterates variable to loop around window
    """
    if (i + 1) == len(window): # if we are at the end of our window
        return 0 # reset to beginning
    return i + 1 # iterate by 1

def decrement_variable(i):
    """
    Properly decrements variable to loop around window
    """
    if (i - 1) < 0: # if we are at the end of our window
        return 9 # reset to beginning
    else:
        return i - 1 # iterate by 1
    

if __name__ == "__main__":
    args = docopt(__doc__)
    #print(args)

    # Setup Sliding window vars
    ack_index = 0
    send_index = 0
    last_send = 9
    seq_num = int(window[0])


    # Open file to transfer
    infile = open(args['<inFile>'])

    # Create packets to be sent (I am aware the algorithm is less efficient) 
    messages = [bytes(line, 'utf-8') for line in infile]
    message_index = 0

    # Grab socket Info to use during sending
    UDP_IP = socket.gethostbyname(args["<destIP>"])
    UDP_PORT = 5432
    

    # Display to user the args used
    print(f"Infile: {args['<inFile>']}")
    print(f"IP: {UDP_IP}\nPORT: {UDP_PORT}")

    # Open socket to write to
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((socket.gethostbyname('10.0.0.1'), UDP_PORT))
    sock.settimeout(.1)
    
    RESYNC_REQ = bytes("Resync", "utf-8")

    start = time.time()
    elapsed = 0 
    dont_wait = True

    # For each index of the messages to be sent 
    while message_index < len(messages):
        
        # Receive in 10 second chunks and check if we can send
        while elapsed < 10 and message_index < len(messages): 
            sock.settimeout(.1) # Reset time out due to race condition in socket module
            # Only send bytes in frame of Sliding Window Algorithm
            
            if dont_wait == True: # if we are not waiting
                seq_num = int(window[send_index]) # grab the current sequence num
                message = bytes(str(seq_num)+" ", "utf-8") 
                message += messages[message_index] # build our message
                sock.sendto(message, (UDP_IP, UDP_PORT)) # Send a packet to the server
                print(f"Sending: ACK index: {ack_index}, Send_index: {send_index}, End_index: {last_send},  Seq_num: {seq_num}")
                #if(send_index < last_send):
                send_index = iterate_variable(send_index) # iterate our sending index by 1
                if send_index == last_send: # if we are at the end of the sliding glass door
                    dont_wait = False
                message_index+=1 # Grab next message to send
                         
            # Process ready to receive requests
            try:
                data, server = sock.recvfrom(1024) # Try to receive a ack message
                elapsed = 0 # If we received a message reset our timer
                data = data.decode('utf-8') # grab bytes as string
                
                if 'RTR' in data: # validate correct sync
                   
                    rtr = int(data[4:]) # grab ack number and compare to ours
                    print(f"Receiving: ACK index: {ack_index}, Send_index: {send_index}, End_index: {last_send},  Seq_num: {seq_num}, Rtr: {rtr}")
                    
                    # Processes acknowledgement
                    if rtr == (iterate_variable(ack_index)): # if RTR is 1 more than our ack index
                        print(f"ACKED RTR:{rtr} ACK:{ack_index}")
                        ack_index = iterate_variable(ack_index) # ACK the current index by moving ack_index by 1
                        last_send = iterate_variable(last_send) # move our ending frame by 1 when ack_index moves
                        print(f"NEW: ACK index: {ack_index}, Send_index: {send_index}, End_index: {last_send}")
                        if dont_wait == False: 
                            print("dont wait set to true")
                            send_index = iterate_variable(send_index)
                            dont_wait = True
                    else:
                        #resyc
                        # Process ready to request and move send_index down to rtr
                        # also move the message index down everytime we move send_index
                        print(f"Resyncing...      elapsed:{elapsed}, rtr:{rtr}, sendindex: {send_index}, messageindex: {message_index}")
                        send_index, message_index = resync_index(send_index, message_index, rtr) 
                        if dont_wait == False: 
                            dont_wait = True
            
            except socket.timeout: # If socket timed out (nothing read)
                end = time.time() 
                elapsed = end - start # decrement time
        
        
        # Completed the sending of the file
        if message_index >= len(messages):
            print("Read it all")
            break
        elif elapsed >= 10: # We have timed out and need to resync our packets to transmit
            print("Need to resync")
    
            elapsed = 0
            origsend = send_index

            sock.sendto(RESYNC_REQ, (UDP_IP, UDP_PORT)) # Send our resync
            
            while(True): # Try to receive RTR Poll
                try:
                    sock.sendto(RESYNC_REQ, (UDP_IP, UDP_PORT))
                    data, server = sock.recvfrom(1024)
                    print(f"Data: {data}")
                    break;
                except socket.timeout:
                    print("Socket timed out")
                    
                if(len(data) == 0):
                    break
            data = data.decode('utf-8') # grab bytes as string
            rtr = int(data[4:]) # grab ack number and compare to ours
            if (send_index != rtr): # If we need to resynce
                send_index, message_index = resync_index(send_index, message_index, rtr) 
                print(f"************ Resynced ***************\n RTR:{rtr}, sendindex:{origsend} to {send_index}")
            
            # Reset the waiting
            dont_wait = True


    sock.sendto(bytes(f"0xffff", 'utf-8'), (UDP_IP, UDP_PORT))
    infile.close()

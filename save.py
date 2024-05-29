import cv2
    
def save_loop(queue):
    while True:
        try:
            log_id, img = queue.get()
        
            cv2.imwrite(f"log/{log_id}.jpg", img)
        except:
            print("Unable to save")
            
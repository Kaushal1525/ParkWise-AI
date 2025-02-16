import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import json
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import qrcode
import cv2
from pyzbar.pyzbar import decode
from PIL import Image, ImageTk  # Ensure this import is at the top


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip, text=self.text,
                         justify='left',
                         background="#ffffe0",
                         relief='solid',
                         borderwidth=1,
                         font=("Arial", "10", "normal"))
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class ParkingSystem:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("ParkWise AI")
        self.window.geometry("1200x800")

        self.total_spots = 25
        self.parking_spots = [False] * self.total_spots
        self.parked_cars = {}
        self.history = []

        self.load_parking_history()
        self.create_gui()

    def load_parking_history(self):
        if os.path.exists("parking_history.json"):
            with open("parking_history.json", "r") as file:
                self.history = json.load(file)
        else:
            self.history = []

    def save_parking_history(self):
        with open("parking_history.json", "w") as file:
            json.dump(self.history, file, indent=4)

    def create_gui(self):
        title = tk.Label(self.window, text="ParkWise AI", font=("Arial", 24, "bold"))
        title.pack(pady=20)

        self.spots_frame = tk.Frame(self.window)
        self.spots_frame.pack(pady=20)

        self.available_spots_label = tk.Label(self.window,
                                              text=f"Available Spots: {self.total_spots}",
                                              font=("Arial", 14, "bold"))
        self.available_spots_label.pack(pady=10)

        self.update_spots_display()

        entry_frame = tk.Frame(self.window)
        entry_frame.pack(pady=20)

        tk.Label(entry_frame, text="Car Number:", font=("Arial", 12)).grid(row=0, column=0, padx=5)
        self.car_number_entry = tk.Entry(entry_frame, font=("Arial", 12))
        self.car_number_entry.grid(row=0, column=1, padx=5)

        tk.Button(entry_frame, text="Park Car",
                  command=self.park_car,
                  font=("Arial", 12),
                  bg="#4CAF50",
                  fg="white",
                  width=12).grid(row=0, column=2, padx=5)

        tk.Button(entry_frame, text="Remove Car",
                  command=self.remove_car,
                  font=("Arial", 12),
                  bg="#f44336",
                  fg="white",
                  width=12).grid(row=0, column=3, padx=5)

        tk.Button(entry_frame, text="Scan QR Code",
                  command=self.scan_qr_code,
                  font=("Arial", 12),
                  bg="#2196F3",
                  fg="white",
                  width=12).grid(row=0, column=4, padx=5)

        self.status_label = tk.Label(self.window, text="Welcome to ParkWise AI",
                                     font=("Arial", 14), fg="#333")
        self.status_label.pack(pady=10)

        self.history_frame = tk.Frame(self.window)
        self.history_frame.pack(pady=20)

        tk.Label(self.history_frame, text="Parking History:", font=("Arial", 14)).pack()
        self.history_listbox = tk.Listbox(self.history_frame, width=80, height=10)
        self.history_listbox.pack(pady=10)
        self.update_history_display()

    def update_history_display(self):
        self.history_listbox.delete(0, tk.END)
        for record in self.history:
            self.history_listbox.insert(tk.END, f"{record['car_number']} - {record['action']} at {record['time']}")

    def update_spots_display(self):
        for widget in self.spots_frame.winfo_children():
            widget.destroy()

        for i in range(self.total_spots):
            color = "#ff6b6b" if self.parking_spots[i] else "#7bed9f"
            status = "Occupied" if self.parking_spots[i] else "Empty"
            spot_frame = tk.Frame(self.spots_frame, relief=tk.RAISED, borderwidth=1)
            spot_frame.grid(row=i // 10, column=i % 10, padx=5, pady=5)

            row_label = "1-" if i // 10 == 0 else "2-" if i // 10 == 1 else "3-"
            spot_number = f"{row_label}{i % 10 + 1}"

            spot_label = tk.Label(spot_frame,
                                  text=f"Spot {spot_number}",
                                  bg=color,
                                  width=12,
                                  height=2,
                                  font=("Arial", 10, "bold"))
            spot_label.pack(pady=2)

            status_label = tk.Label(spot_frame,
                                    text=status,
                                    width=12,
                                    font=("Arial", 9))
            status_label.pack(pady=2)

            if self.parking_spots[i]:
                car_number = next((car for car, details in self.parked_cars.items()
                                   if details["spot"] == i), "")
                entry_time = self.parked_cars[car_number]["entry_time"]

                tooltip_text = f"Car Number: {car_number}\nParked since: {entry_time.strftime('%I:%M %p')}"

                Tooltip(spot_label, tooltip_text)
                Tooltip(status_label, tooltip_text)

                tk.Label(spot_frame,
                         text=car_number[:8] + "..." if len(car_number) > 8 else car_number,
                         width=12,
                         font=("Arial", 8)).pack(pady=1)

        self.available_spots_label.config(
            text=f"Available Spots: {self.total_spots - sum(self.parking_spots)}")

    def find_empty_spot(self):
        for i in range(self.total_spots):
            if not self.parking_spots[i]:
                return i
        return -1

    def park_car(self):
        car_number = self.car_number_entry.get().strip().upper()

        if not car_number:
            messagebox.showerror("Error", "Please enter a car number")
            return

        if car_number in self.parked_cars:
            messagebox.showerror("Error", "This car is already parked")
            return

        spot = self.find_empty_spot()
        if spot == -1:
            messagebox.showerror("Error", "Parking is full")
            return

        self.parking_spots[spot] = True
        self.parked_cars[car_number] = {
            "spot": spot,
            "entry_time": datetime.now()
        }

        self.generate_qr_code(car_number, spot)

        self.history.append({
            "car_number": car_number,
            "action": "Parked",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        self.save_parking_history()

        row_label = "1-" if spot // 10 == 0 else "2-" if spot // 10 == 1 else "3-"
        spot_number = f"{row_label}{spot % 10 + 1}"

        self.update_spots_display()
        self.status_label.config(
            text=f"Car {car_number} parked at spot {spot_number}",
            fg="#4CAF50")
        self.car_number_entry.delete(0, tk.END)
        self.update_history_display()

    def remove_car(self):
        car_number = self.car_number_entry.get().strip().upper()

        if not car_number:
            messagebox.showerror("Error", "Please enter a car number")
            return

        if car_number not in self.parked_cars:
            messagebox.showerror("Error", "This car is not parked here")
            return

        spot = self.parked_cars[car_number]["spot"]
        entry_time = self.parked_cars[car_number]["entry_time"]
        duration = datetime.now() - entry_time
        hours = duration.total_seconds() / 3600
        fee = round(hours * 10, 2)

        row_label = "1-" if spot // 10 == 0 else "2-" if spot // 10 == 1 else "3-"
        spot_number = f"{row_label}{spot % 10 + 1}"

        self.parking_spots[spot] = False
        del self.parked_cars[car_number]

        self.history.append({
            "car_number": car_number,
            "action": "Removed",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        self.save_parking_history()

        self.generate_receipt(car_number, spot_number, entry_time, fee)

        self.update_spots_display()
        self.status_label.config(
            text=f"Car {car_number} removed from spot {spot_number}. Parking Fee: ${fee}",
            fg="#f44336")
        self.car_number_entry.delete(0, tk.END)
        self.update_history_display()

    def generate_qr_code(self, car_number, spot):
        spot_label = "1-" if spot // 10 == 0 else "2-" if spot // 10 == 1 else "3-"
        spot_number = f"{spot_label}{spot % 10 + 1}"
        qr_data = f"{car_number},{spot_number}"
        qr = qrcode.make(qr_data)
        qr.save(f"{car_number}_qr.png")
        messagebox.showinfo("QR Code Generated", f"QR Code saved as {car_number}_qr.png")

    def scan_qr_code(self):
        self.scan_window = tk.Toplevel(self.window)
        self.scan_window.title("QR Code Scanner")

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Open the camera with DSHOW backend
        self.video_label = tk.Label(self.scan_window)
        self.video_label.pack()

        # Label to display scanned information
        self.scanned_info_label = tk.Label(self.scan_window, text="", font=("Arial", 14))
        self.scanned_info_label.pack(pady=10)

        def update_frame():
            ret, frame = cap.read()
            if ret:
                decoded_objects = decode(frame)
                for obj in decoded_objects:
                    qr_data = obj.data.decode('utf-8')
                    car_number, spot_number = qr_data.split(',')

                    # Update the scanned information label
                    self.scanned_info_label.config(text=f"Scanned: Car Number: {car_number}, Spot: {spot_number}")

                    # Populate the car number entry field
                    self.car_number_entry.delete(0, tk.END)
                    self.car_number_entry.insert(0, car_number)

                    # Check if the car is parked
                    if car_number in self.parked_cars:
                        messagebox.showinfo("Check-In Status", f"Car {car_number} is checked in at spot {spot_number}.")
                    else:
                        messagebox.showinfo("Check-Out Status", f"Car {car_number} is not parked. Please check out.")

                    # Release the camera and close the scanning window
                    cap.release()
                    self.scan_window.destroy()
                    return

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)

            self.video_label.after(10, update_frame)

        update_frame()

    def generate_receipt(self, car_number, spot_number, entry_time, fee):
        remove_time = datetime.now()
        pdf_filename = f"{car_number}_receipt.pdf"

        c = canvas.Canvas(pdf_filename, pagesize=letter)
        c.drawString(100, 750, "Parking Receipt")
        c.drawString(100, 730, f"Car Number: {car_number}")
        c.drawString(100, 710, f"Spot Number: {spot_number}")
        c.drawString(100, 690, f"Parking Date: {entry_time.strftime('%Y-%m-%d')}")
        c.drawString(100, 670, f"Parking Time: {entry_time.strftime('%H:%M:%S')}")
        c.drawString(100, 650, f"Remove Time: {remove_time.strftime('%H:%M:%S')}")
        c.drawString(100, 630, f"Parking Fee: ${fee:.2f}")

        c.save()
        messagebox.showinfo("Receipt Generated", f"Receipt saved as {pdf_filename}")

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    parking_system = ParkingSystem()
    parking_system.run()
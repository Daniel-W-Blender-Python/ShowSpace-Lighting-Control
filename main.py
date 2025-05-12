# import tkinter as tk
from tkinter import ttk
import tkinter as tk
from tkinter import filedialog
from tkinter import font
from tkinter import messagebox
import json
#from dmx_patch import DmxPatchWindow
from PIL import Image, ImageTk, ImageEnhance
import numpy as np
import serial.tools.list_ports
import time
import sys
import os
import pathlib
import ctypes
#from light_control import LightControl

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ShowSpace.App")


class DmxPatchWindow:
    def __init__(self, new_window):
        self.new_window = new_window
        self.instruments = []
        self.last_clicked_instrument = None
        self.selected_instrument = None
        self.instrument_title_box = None
        self.dmx_address_box = None
        self.instrument_output_vars = {}  # Store StringVar for each instrument
        self.instrument_output_menus = {}  # Store OptionMenu for each instrument
        self.instrument_number = -1
        self.instrument_names = []
        self.instrument_addresses = []
        self.instrument_outputs = []
        self.instrument_y_position = 0
        appdata_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "ShowSpace")
        self.dmx_patch_dir = pathlib.PureWindowsPath(str(os.path.join(appdata_dir, "active_dmx_patch.json"))).as_posix()


    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
    
        return os.path.join(base_path, relative_path)

    def exit_instrument_textbox(self, event, patch_details):
        instrument_title = self.instrument_title_box.get("1.0", tk.END).strip()
        dmx_address = self.dmx_address_box.get("1.0", tk.END).strip()
        output_text = self.instrument_output_vars.get(self.selected_instrument, tk.StringVar()).get()
        self.selected_instrument.config(text=instrument_title + (" " * (80 - len(instrument_title))) + dmx_address + (" " * (80 - len(dmx_address))) + output_text)

        # Update the instrument_names and instrument_addresses lists
        if self.selected_instrument in self.instruments:
            index = self.instruments.index(self.selected_instrument)
            if index < len(self.instrument_names):
                self.instrument_names[index] = instrument_title
            else:
                self.instrument_names.append(instrument_title)
            if index < len(self.instrument_addresses):
                self.instrument_addresses[index] = dmx_address
            else:
                self.instrument_addresses.append(dmx_address)

        patch_details.focus_set()
        return "break"

    def exit_dmx_textbox(self, event, patch_details):
        dmx_address = self.dmx_address_box.get("1.0", tk.END).strip()
        instrument_title = self.instrument_title_box.get("1.0", tk.END).strip()
        output_text = self.instrument_output_vars.get(self.selected_instrument, tk.StringVar()).get()
        self.selected_instrument.config(text=instrument_title + (" " * (80 - len(instrument_title))) + dmx_address + (" " * (80 - len(dmx_address))) + output_text)

        # Update the instrument_addresses and instrument_names lists
        if self.selected_instrument in self.instruments:
            index = self.instruments.index(self.selected_instrument)
            if index < len(self.instrument_addresses):
                self.instrument_addresses[index] = dmx_address
            else:
                self.instrument_addresses.append(dmx_address)
            if index < len(self.instrument_names):
                self.instrument_names[index] = instrument_title
            else:
                self.instrument_names.append(instrument_title)

        patch_details.focus_set()
        return "break"

    def update_patch_scroll_region(self, patch_scrollable_frame, patch_scroll):
        patch_scrollable_frame.update_idletasks()
        patch_scroll.config(scrollregion=patch_scroll.bbox("all"))

    def show_instrument_context_menu(self, event, button, patch_frame, patch_scroll):
        context_menu = tk.Menu(button, tearoff=0)
        context_menu.add_command(label="Delete", command=lambda: self.delete_instrument(button, patch_scroll, patch_frame))
        context_menu.post(event.x_root, event.y_root)

    def delete_instrument(self, button, patch_scroll, patch_frame):
        index = self.instruments.index(button)
        self.instruments.remove(button)

        if button in self.instrument_output_menus:
            self.instrument_output_menus[button].destroy()
            del self.instrument_output_menus[button]
            del self.instrument_output_vars[button] # Also remove the associated StringVar

        if self.last_clicked_instrument == button:
            self.last_clicked_instrument = None

        button.destroy()

        for i in range(index, len(self.instruments)):
            self.instruments[i].grid_configure(row=i)

        self.update_patch_scroll_region(patch_frame, patch_scroll)

    
    def add_instrument(self, patch_scrollable_frame, patch_scroll, patch_details):
        button = tk.Button(patch_scrollable_frame, text="", fg="white", bg="gray25", compound="left", width=780, height=2, anchor="w")
        button.grid(row=self.instrument_y_position, column=0, sticky="w", pady=0)

        self.instruments.append(button)

        instrument_output_var = tk.StringVar(value="Dimmer")
        self.instrument_output_vars[button] = instrument_output_var

        options = ["Dimmer", "Altman_PHX-RGBW", "ETC_ColorSource_Cyc-RGBA", "ETC_ColorSource_PAR-RGBA", "ETC_ColorSource_Spot-RGBIL"]
        output_menu = ttk.OptionMenu(patch_scrollable_frame, instrument_output_var, "Dimmer", *options)
        output_menu.grid(row=self.instrument_y_position, column=1, sticky="ew", padx=5)
        self.instrument_output_menus[button] = output_menu

        self.instrument_y_position += 1
        self.update_patch_scroll_region(patch_scrollable_frame, patch_scroll)

        def update_button_text(*args):
            instrument_name = ""
            dmx_address = ""
            if button in self.instruments:
                instrument_index = self.instruments.index(button)
                instrument_name = self.instrument_names[instrument_index] if instrument_index < len(self.instrument_names) else ""
                dmx_address = self.instrument_addresses[instrument_index] if instrument_index < len(self.instrument_addresses) else ""
            output_text = instrument_output_var.get()
            button.config(text=(instrument_name + (" " * (80 - len(instrument_name))) + dmx_address + (" " * (80 - len(dmx_address))) + output_text))

        instrument_output_var.trace_add("write", update_button_text)

        if self.instrument_number != -1:
            button.config(text=(self.instrument_names[self.instrument_number] + (" " * (80 - len(self.instrument_names[self.instrument_number]))) + self.instrument_addresses[self.instrument_number] + (" " * (80 - len(self.instrument_addresses[self.instrument_number]))) + self.instrument_outputs[self.instrument_number]))
            instrument_output_var.set(self.instrument_outputs[self.instrument_number])
            update_button_text() # Initial update when loading

        button.bind("<Button-3>", lambda event: self.show_instrument_context_menu(event, button, patch_scrollable_frame, patch_scroll))

        def on_click_instrument(event):
            if self.last_clicked_instrument is not None:
                self.last_clicked_instrument.config(bg="gray25", fg="white")

            button.config(bg="white", fg="black")
            self.last_clicked_instrument = button
            self.selected_instrument = button

            helv363 = font.Font(family='Helvetica', size=12)

            instrument_title_label = tk.Label(patch_details, text="Name", bg="gray10", fg="white", font=helv363, relief=tk.SOLID, borderwidth=0)
            instrument_title_label.place(x=0, y=10, width=80, height=20)

            dmx_address_label = tk.Label(patch_details, text="Address(es)", bg="gray10", fg="white", font=helv363, relief=tk.SOLID, borderwidth=0)
            dmx_address_label.place(x=20, y=50, width=80, height=20)

            self.instrument_title_box = tk.Text(patch_details, height=1, width=50)
            self.instrument_title_box.place(x=120, y=10)

            self.dmx_address_box = tk.Text(patch_details, height=1, width=50)
            self.dmx_address_box.place(x=120, y=50)

            instrument_title = self.selected_instrument.cget("text")[:35].strip()
            self.instrument_title_box.insert("1.0", instrument_title)
            self.instrument_title_box.bind("<Return>", lambda event: self.exit_instrument_textbox(event, patch_details))

            dmx_address = self.selected_instrument.cget("text")[75:95].strip()
            self.dmx_address_box.insert("1.0", dmx_address)
            self.dmx_address_box.bind("<Return>", lambda event: self.exit_dmx_textbox(event, patch_details))

            output_label = tk.Label(patch_details, text="Output", bg="gray10", fg="white", font=helv363, relief=tk.SOLID, borderwidth=0)
            output_label.place(x=20, y=90)

            options = ["Dimmer", "Altman_PHX-RGBW", "ETC_ColorSource_Cyc-RGBA", "ETC_ColorSource_PAR-RGBA", "ETC_ColorSource_Spot-RGBIL"]

            for widget in patch_details.winfo_children():
                if isinstance(widget, ttk.OptionMenu):
                    widget.destroy()

            current_output = self.instrument_output_vars.get(button, tk.StringVar()).get()
            output_menu = ttk.OptionMenu(patch_details, self.instrument_output_vars[button], current_output, *options)
            output_menu.place(x=120, y=90)

        button.bind("<Button-1>", on_click_instrument)
    def load_patch(self, dmx_patch_data, patch_scrollable_frame, patch_scroll, patch_details):
        self.instruments = []
        self.instrument_output_vars = {}
        self.instrument_output_menus = {}
        self.instrument_names = []
        self.instrument_addresses = []
        self.instrument_outputs = []

        if len(dmx_patch_data["Name"]) > 0:
            for i in range(len(dmx_patch_data["Name"])):
                self.instrument_names.append(dmx_patch_data["Name"][i])
                self.instrument_addresses.append(dmx_patch_data["Address"][i])
                self.instrument_outputs.append(dmx_patch_data["Output"][i])
                self.instrument_number = i
                self.add_instrument(patch_scrollable_frame, patch_scroll, patch_details)
            self.instrument_number = -1

        self.update_patch_scroll_region(patch_scrollable_frame, patch_scroll)

    def dmx_patch(self, new_window):
        self.top = tk.Toplevel(new_window)
        self.top.title("DMX Patch")
        self.top.geometry("800x600+50+100")
        self.top.configure(bg="gray10")

        patch_canvas = tk.Canvas(self.top, bg="gray10", height=600)
        patch_canvas.pack(fill=tk.BOTH, expand=True)

        patch_frame = tk.Frame(patch_canvas, bg="gray10", width=800, height=400)
        patch_frame.place(x=0, y=0)

        patch_canvas.create_window((0, 75), window=patch_frame, anchor="nw")

        patch_scroll = tk.Canvas(patch_frame, width=780, height=350, bg="gray20")
        patch_scroll.pack(side="left", fill="both", expand=True)

        patch_scroll_y = tk.Scrollbar(patch_frame, orient="vertical", command=patch_scroll.yview)
        patch_scroll_y.pack(side="right", fill="y")

        patch_scroll.config(yscrollcommand=patch_scroll_y.set)

        patch_scrollable_frame = tk.Frame(patch_scroll)
        patch_scroll.create_window((0, 0), window=patch_scrollable_frame, anchor="nw")

        patch_details = tk.Frame(patch_canvas, bg="gray10", borderwidth=0, relief="solid", width=800, height=175, highlightbackground="white", highlightcolor="white", highlightthickness=2)
        patch_details.place(x=0, y=425)

        helv363 = font.Font(family='Helvetica', size=12)

        new_instrument_button = tk.Button(self.top, text="New Instrument", bg="gray25", fg="white", font=helv363, activebackground="white", command=lambda : self.add_instrument(patch_scrollable_frame, patch_scroll, patch_details))
        new_instrument_button.place(x=15, y=10)

        patch_info = tk.Frame(self.top, bg="white", borderwidth=0, relief="solid", width=800, height=20)
        patch_info.place(x=0, y=50)

        instrument_name_text = tk.Label(patch_info, text="Instrument Name", bg="white", fg="black", relief=tk.SOLID)
        instrument_name_text.place(x=0, y=0, width=225, height=20)

        addresses_text = tk.Label(patch_info, text="Address(es)", bg="white", fg="black", relief=tk.SOLID)
        addresses_text.place(x=225, y=0, width=125, height=20)

        dmx_output_text = tk.Label(patch_info, text="DMX Output", bg="white", fg="black", relief=tk.SOLID)
        dmx_output_text.place(x=350, y=0, width=450, height=20)

        active_dmx_patch_file = open(self.dmx_patch_dir)
        active_dmx_patch_data = json.load(active_dmx_patch_file)

        self.load_patch(active_dmx_patch_data, patch_scrollable_frame, patch_scroll, patch_details)

        def update_patch():
            active_dmx_patch_file = open(self.dmx_patch_dir)
            active_dmx_patch_data = json.load(active_dmx_patch_file)

            active_dmx_patch_data["Name"] = []
            active_dmx_patch_data["Address"] = []
            active_dmx_patch_data["Output"] = []

            for button in self.instruments:
                instrument_name = button.cget("text")[:35].strip()
                dmx_address = button.cget("text")[75:95].strip()
                output = self.instrument_output_vars.get(button, tk.StringVar()).get()
                active_dmx_patch_data["Name"].append(instrument_name)
                active_dmx_patch_data["Address"].append(dmx_address)
                active_dmx_patch_data["Output"].append(output)

            active_dmx_patch_file.seek(0)
            with open(self.dmx_patch_dir, "w") as file:
                json.dump(active_dmx_patch_data, file, indent=4)
            active_dmx_patch_file.truncate()
            active_dmx_patch_file.close()

            self.instrument_names = []
            self.instrument_addresses = []
            self.instrument_outputs = []

            print("DMX patch updated successfully!")
            self.top.destroy()

        submit_button = tk.Button(self.top, text="Update", bg="gray75", command=update_patch)
        submit_button.place(x=735, y=565)

        try:
            icon_path = pathlib.PureWindowsPath(self.resource_path("Data/ShowSpace_Logo.ico")).as_posix()
            self.top.iconbitmap(icon_path)
        except:
            messagebox.showerror("Icon Not Shown", "Try Something Else")

        self.top.mainloop()


class StartWindow:
    def __init__(self, script_scroll=None, control_scroll=None, script_scroll_y=None, control_scroll_y=None, selected_cue=None, last_clicked_button=None, light_control_scroll=None, light_control_scroll_y=None, light_frame=None, last_clicked_instrument=None, selected_output=None, dmx_address_box=None, instrument_title_box=None):
        self = self
        self.script_scroll = script_scroll
        self.control_scroll = control_scroll
        self.script_scroll_y = script_scroll_y
        self.control_scroll_y = control_scroll_y
        self.selected_cue = selected_cue
        self.cues = []
        self.last_clicked_button = last_clicked_button
        self.light_control_scroll = light_control_scroll
        self.light_control_scroll_y = light_control_scroll_y
        self.light_frame = light_frame
        self.lights = []
        self.light_types = []
        self.light_addresses = []
        self.last_clicked_light = None
        self.selected_light = None
        self.light_y_position = 0
        self.light_names = []
        self.light_color = None
        self.color_image = None
        self.color_wheel_canvas = None
        self.brightness_scale = 0
        self.light_dashboard = False
        self.light_button = None
        self.cue_vals = []
        self.cue_durations = []
        self.cue_duration = "00:05:00"
        self.dmx = None
        self.is_new_workspace = True
        self.cue_load_number = 0
        appdata_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "ShowSpace")
        self.dmx_patch_dir = pathlib.PureWindowsPath(str(os.path.join(appdata_dir, "active_dmx_patch.json"))).as_posix()


    
    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
    
        return os.path.join(base_path, relative_path)



    def find_usb_serial_port(self):
        ports = list(serial.tools.list_ports.comports())
        for port, desc, hwid in sorted(ports): #sorting ports for consistency
            if "USB Serial" in desc or "USB-SERIAL" in desc or "USB UART" in desc or "CDC ACM" in desc or "CP210" in desc or "FTDI" in desc : #common usb serial descriptors
                return port
            if "VID:PID" in hwid: #checking hardware ID
                if "VID_10C4" in hwid or "VID_0403" in hwid or "VID_239A" in hwid or "VID_067B" in hwid: #common VID for usb serial
                    return port
        return None


    def show_color(self, event):
        """Update the color preview when the mouse moves over the color wheel."""
        x = event.x
        y = event.y
            
        # Check if the coordinates are within the image bounds
        if np.sqrt(((x-200)**2) + ((y-200)**2)) < 200:
            try:
                r, g, b = self.color_image.getpixel((x, y))
    
                # Adjust the brightness based on the slider value
                brightness = self.brightness_scale.get() / 100.0  # Brightness from 0.0 to 1.0
                    
                # Create a darkened image for the color wheel
                enhancer = ImageEnhance.Brightness(self.color_image)
                darkened_image = enhancer.enhance(brightness)
                global color_wheel_image
                color_wheel_image = ImageTk.PhotoImage(darkened_image)
                self.color_wheel_canvas.create_image(0, 0, anchor=tk.NW, image=color_wheel_image)
    
                # Get the color value from the darkened image
                r, g, b = darkened_image.getpixel((x, y))  
                    
                # Update the circle position to indicate the selected color
                circle_radius = 8
                hex_color = self.rgb_to_hex(r, g, b)
                circle_x1 = x - circle_radius
                circle_y1 = y - circle_radius
                circle_x2 = x + circle_radius
                circle_y2 = y + circle_radius
                    
                # Redraw the cursor circle at the new position
                cursor_circle = self.color_wheel_canvas.create_oval(circle_x1, circle_y1, circle_x2, circle_y2, outline="white", width=3)
    
            except IndexError:
                pass

    def pick_color(self, event):
        """Set the selected color when the user clicks on the color wheel."""
        x = event.x
        y = event.y
            
        # Get the RGB color values of the clicked position
        if 0 <= x < self.color_image.width and 0 <= y < self.color_image.height:
            r, g, b = self.color_image.getpixel((x, y))
    
            # Adjust the brightness based on the slider value
            brightness = self.brightness_scale.get() / 100.0  
            enhancer = ImageEnhance.Brightness(self.color_image)
            darkened_image = enhancer.enhance(brightness)
            global color_wheel_image
            color_wheel_image = ImageTk.PhotoImage(darkened_image)
            self.color_wheel_canvas.create_image(0, 0, anchor=tk.NW, image=color_wheel_image)
    
            # Get the RGB color from the darkened image
            r, g, b = darkened_image.getpixel((x, y))  
    
            # Update the background color with the selected color
            self.light_color = [r, g, b]

            print(self.light_color)

            if self.light_types[self.lights.index(self.light_button)] == "ETC_ColorSource_Cyc-RGBA":
                start_str, end_str = self.light_addresses[self.lights.index(self.light_button)].split('-')
                start = int(start_str)
                end = int(end_str)

                print(list(range(start, end + 1))[0])
                print(self.light_color[0])

                try:
                    self.dmx = DMXConnection(usb_port)
                except:
                    print("No DMX Device")

                if self.dmx is not None:
                    self.dmx.set_channel(int(list(range(start, end + 1))[0]-1), int(self.light_color[0]))
                    self.dmx.set_channel(int(list(range(start, end + 1))[1]-1), int(self.light_color[1]))
                    self.dmx.set_channel(int(list(range(start, end + 1))[2]-1), int(self.light_color[2]))
                    self.dmx.set_channel(int(list(range(start, end + 1))[3]-1), int(0.7*self.light_color[0]+0.3*self.light_color[1]))
                    self.dmx.render()

                print("Cue Vals: ", self.cue_vals)
                for n in range(4):
                    self.light_color.append(int(list(range(start, end + 1))[n]-1))
                self.cue_vals[self.cues.index(self.selected_cue)][self.lights.index(self.light_button)] = self.light_color
                
                    
            elif self.light_types[self.lights.index(self.light_button)] == "Altman_PHX-RGBW":
                start_str, end_str = self.light_addresses[self.lights.index(self.light_button)].split('-')
                start = int(start_str)
                end = int(end_str)

                try:
                    self.dmx = DMXConnection(usb_port)
                except:
                    print("No DMX Device")

                if self.dmx is not None:
                    self.dmx.set_channel(int(list(range(start, end + 1))[0]-1), int(self.light_color[0]))
                    self.dmx.set_channel(int(list(range(start, end + 1))[1]-1), int(self.light_color[1]))
                    self.dmx.set_channel(int(list(range(start, end + 1))[2]-1), int(self.light_color[2]))
                    self.dmx.set_channel(int(list(range(start, end + 1))[3]-1), int(min(self.light_color)))
                    self.dmx.render()

                print("Cue Vals: ", self.cue_vals)
                for n in range(4):
                    self.light_color.append(int(list(range(start, end + 1))[n]-1))
                self.cue_vals[self.cues.index(self.selected_cue)][self.lights.index(self.light_button)] = self.light_color

            elif self.light_types[self.lights.index(self.light_button)] == "ETC_ColorSource_Spot-RGBIL":
                start_str, end_str = self.light_addresses[self.lights.index(self.light_button)].split('-')
                start = int(start_str)
                end = int(end_str)

                try:
                    self.dmx = DMXConnection(usb_port)
                except:
                    print("No DMX Device")

                if self.dmx is not None:
                    self.dmx.set_channel(int(list(range(start, end + 1))[0]), int(self.light_color[0]))
                    self.dmx.set_channel(int(list(range(start, end + 1))[1]), int(self.light_color[1]))
                    self.dmx.set_channel(int(list(range(start, end + 1))[2]), int(self.light_color[2]))
                    self.dmx.set_channel(int(list(range(start, end + 1))[3]), int(0.6*self.light_color[2]+0.4*self.light_color[0]))
                    self.dmx.set_channel(int(list(range(start, end + 1))[4]), int(0.8*self.light_color[1]+0.2*self.light_color[0]))
                    self.dmx.render()

                print("Cue Vals: ", self.cue_vals)
                for n in range(5):
                    self.light_color.append(int(list(range(start, end + 1))[n]-1))
                self.cue_vals[self.cues.index(self.selected_cue)][self.lights.index(self.light_button)] = self.light_color


    def rgb_to_hex(self, r, g, b):
        """Convert RGB values to hex format."""
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def update_color_wheel(self, brightness):
        """Update the color wheel image with the given brightness."""
        enhancer = ImageEnhance.Brightness(self.color_image)
        darkened_image = enhancer.enhance(brightness)
        global color_wheel_image
        color_wheel_image = ImageTk.PhotoImage(darkened_image)
        self.color_wheel_canvas.create_image(0, 0, anchor=tk.NW, image=color_wheel_image)

        
    def open(self):
        root = tk.Tk()

        # Create a menu bar
        menubar = tk.Menu(root)

        # Create the file menu
        filemenu = tk.Menu(menubar, tearoff=0)

        def open_file():
            file_path = filedialog.askopenfilename()
            if file_path:
                print("Selected file:", file_path)
            return file_path

        def save_as_file():
                custom_extension = ".showspace"
                file_path = filedialog.asksaveasfilename(
                    defaultextension=custom_extension,
                    filetypes=[(f"ShowSpace Files", f"*{custom_extension}"), ("JSON Files", "*.json"), ("All Files", "*.*")]
                )
                if file_path:
                    try:
                        cue_text = []
                        for cue in self.cues:
                            cue_text.append(cue.cget('text'))
                        data_to_save = {
                            "cue_text": cue_text,
                            "cue_vals": self.cue_vals,
                        }
                        with open(file_path, "w") as file:
                            json.dump(data_to_save, file, indent=4)
                        print(f"Patch saved to: {file_path}")
                    except Exception as e:
                        print(f"Error saving patch: {e}")

        def exit_program():
            root.quit()

        def open_new_workspace():
            root.destroy()  # Close the current window
            self.open_new_workspace_window()  # Open the new window

        def open_workspace():
            custom_extension = ".showspace"
            file_path = filedialog.askopenfilename(
                filetypes=[(f"ShowSpace Files", f"*{custom_extension}"), ("JSON Files", "*.json"), ("All Files", "*.*")]
            )
            if file_path:
                with open(file_path, 'r') as file:
                    loaded_data = json.load(file)
                    self.cue_vals = loaded_data.get("cue_vals", [])
                    self.cue_text = loaded_data.get("cue_text", [])
                    self.is_new_workspace = False
                    
                open_new_workspace()


        filemenu.add_command(label="Settings", command=open_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=exit_program)

        menubar.add_cascade(label="File", menu=filemenu)

        # Display the menu
        root.config(menu=menubar)

        root.geometry("800x600+400+100")  # Width, height, x, y coordinates
        root.title("ShowSpace 3D")
        root.configure(bg="black")

        button_frame = tk.Frame(root)
        button_frame.pack(fill=tk.X)

        new_video_image = tk.PhotoImage(file=pathlib.PureWindowsPath(self.resource_path('Data/New Workspace.png')).as_posix())
        new_image_image = tk.PhotoImage(file=pathlib.PureWindowsPath(self.resource_path('Data/Open Workspace.png')).as_posix())

        intro_image = tk.PhotoImage(file=pathlib.PureWindowsPath(self.resource_path('Data/ShowSpace.png')).as_posix())

        intro_message = tk.Label(root, image=intro_image)
        intro_message.place(x=0, y=0)

        new_video_button = tk.Button(root, image=new_video_image, command=open_new_workspace)
        new_video_button.place(x=150, y=400)
        new_image_button = tk.Button(root, image=new_image_image, command=open_workspace)
        new_image_button.place(x=150, y=480)

        icon_path = pathlib.PureWindowsPath(self.resource_path("Data/ShowSpace_Logo.ico")).as_posix()
        root.iconbitmap(icon_path)

        root.mainloop()


    def open_new_workspace_window(self):
        # Create a new window (black background)
        new_window = tk.Tk()

        # Create a menu bar for the new window
        menubar = tk.Menu(new_window)

        # Create the file menu
        filemenu = tk.Menu(menubar, tearoff=0)
        cuemenu = tk.Menu(menubar, tearoff=0)
        patchmenu = tk.Menu(menubar, tearoff=0)

        def exit_textbox(event, cue_title_box, cue_duration_box):
            cue_title = cue_title_box.get("1.0", tk.END).strip()
            cue_duration = cue_duration_box.get("1.0", tk.END).strip()
            cue_text = "Light" + (" "*30) + cue_title + (" "*(140-len(cue_title))) + cue_duration
            print(len(cue_title))
            print(cue_text)
            self.selected_cue.config(text=cue_text)
            cue_info.focus_set()
            return "break"

        def exit_duration_textbox(event, cue_duration_box, cue_title_box, duration_index):
            cue_title = cue_title_box.get("1.0", tk.END).strip()
            cue_duration = cue_duration_box.get("1.0", tk.END).strip()
            cue_text = "Light" + (" "*30) + cue_title + (" "*(140-len(cue_title))) + cue_duration
            self.selected_cue.config(text=cue_text)
            cue_info.focus_set()
            self.cue_durations[duration_index] = int(cue_duration.replace(":", "")) / 100
            return "break"

        def exit_instrument_textbox(event, patch_details):
            instrument_title = self.instrument_title_box.get("1.0", tk.END).strip()
            dmx_address = self.dmx_address_box.get("1.0", tk.END).strip()
            print(self.selected_instrument)
            self.selected_instrument.config(text=instrument_title + (" " * (80 - len(instrument_title)) + dmx_address + (" " * (80-len(dmx_address))) + self.selected_output.get()))
            patch_details.focus_set()
            return "break"

        def exit_dmx_textbox(event, patch_details):
            dmx_address = self.dmx_address_box.get("1.0", tk.END).strip()
            instrument_title = self.instrument_title_box.get("1.0", tk.END).strip()
            print(self.selected_instrument)
            self.selected_instrument.config(text=instrument_title + (" " * (80 - len(instrument_title)) + dmx_address + (" " * (80-len(dmx_address))) + self.selected_output.get()))
            patch_details.focus_set()
            return "break"

    
        def open_file():
            file_path = filedialog.askopenfilename()
            if file_path:
                print("Selected file:", file_path)
            return file_path

        def save_as_file():
                custom_extension = ".showspace"
                file_path = filedialog.asksaveasfilename(
                    defaultextension=custom_extension,
                    filetypes=[(f"ShowSpace Files", f"*{custom_extension}"), ("JSON Files", "*.json"), ("All Files", "*.*")]
                )
                if file_path:
                    try:
                        cue_text = []
                        for cue in self.cues:
                            cue_text.append(cue.cget('text'))
                        data_to_save = {
                            "cue_text": cue_text,
                            "cue_vals": self.cue_vals,
                        }
                        with open(file_path, "w") as file:
                            json.dump(data_to_save, file, indent=4)
                        print(f"Patch saved to: {file_path}")
                    except Exception as e:
                        print(f"Error saving patch: {e}")

        def exit_program():
            new_window.quit()

        def play_cue():
            print(self.cue_vals)

            try:
                self.dmx = DMXConnection(usb_port)
            except:
                print("No DMX Device")

            if self.dmx is not None:
                if self.cues.index(self.selected_cue) != 0:
                    for n in range(int(self.cue_durations[self.cues.index(self.selected_cue)] * 10)):
                        for address in range(len(self.cue_vals[self.cues.index(self.selected_cue)])):
                            print("Channel Address: ", self.cue_vals[self.cues.index(self.selected_cue)][address][3])
                            self.dmx.set_channel(self.cue_vals[self.cues.index(self.selected_cue)][address][3], self.cue_vals[self.cues.index(self.selected_cue)][address][0])
                            self.dmx.set_channel(self.cue_vals[self.cues.index(self.selected_cue)][address][4], self.cue_vals[self.cues.index(self.selected_cue)][address][1])
                            self.dmx.set_channel(self.cue_vals[self.cues.index(self.selected_cue)][address][5], self.cue_vals[self.cues.index(self.selected_cue)][address][2])
                            self.dmx.render()
                        time.sleep(0.1)
                elif self.cues.index(self.selected_cue) == 0:
                    for address in range(len(self.cue_vals[self.cues.index(self.selected_cue)])):
                        print("Channel Address: ", self.cue_vals[self.cues.index(self.selected_cue)][address][3])
                        self.dmx.set_channel(self.cue_vals[self.cues.index(self.selected_cue)][address][3], self.cue_vals[self.cues.index(self.selected_cue)][address][0])
                        self.dmx.set_channel(self.cue_vals[self.cues.index(self.selected_cue)][address][4], self.cue_vals[self.cues.index(self.selected_cue)][address][1])
                        self.dmx.set_channel(self.cue_vals[self.cues.index(self.selected_cue)][address][5], self.cue_vals[self.cues.index(self.selected_cue)][address][2])
                        self.dmx.render()                    

        def open_patch(new_window):
            app = DmxPatchWindow(new_window)
            app.dmx_patch(new_window)

        filemenu.add_command(label="Settings", command=open_file)
        filemenu.add_command(label="Save", command=save_as_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=exit_program)

        cuemenu.add_command(label="Light", command=lambda: add_cue_button(new_window, "Light"))

        patchmenu.add_command(label="DMX Patch", command=lambda: open_patch(new_window))
        

        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Cues", menu=cuemenu)
        menubar.add_cascade(label="Patching", menu=patchmenu)

        new_window.config(menu=menubar)

        new_window.geometry("1600x800+0+0")  # Set window size and position
        new_window.title("New Workspace")
        new_window.configure(bg="black")

        # Create a Canvas for the separator and resizable panels
        canvas = tk.Canvas(new_window, bg="black", height=800)
        canvas.pack(fill=tk.BOTH, expand=True)

        # Panel 1 (left panel, black) - Will be resized
        panel_left = canvas.create_rectangle(0, 0, 800, 800, fill="gray10", outline="black")

        # Panel 2 (right panel, gray, fixed width)
        panel_right = canvas.create_rectangle(800, 0, 1600, 800, fill="gray10", outline="gray")

        helv362 = font.Font(family='Helvetica', size=12)
        helv36 = font.Font(family='Helvetica', size=18)

#        cue_info = canvas.create_rectangle(0, 80, 800, 100, fill="white", outline="gray")
        cue_info = tk.Frame(canvas, bg="white", borderwidth=0, relief="solid", width=800, height=20)
        cue_info.place(x=0, y=100)

        cue_details = tk.Frame(canvas, bg="gray10", borderwidth=0, relief="solid", width=760, height=150, highlightbackground="white", highlightcolor="white", highlightthickness=2)
        cue_details.place(x=20, y=540)

        # Cue List Label (top of the right panel)
        cue_list = tk.PhotoImage(file=pathlib.PureWindowsPath(self.resource_path('Data/Cue List.png')).as_posix())
        cue_list_label = tk.Label(new_window, image=cue_list)
        cue_list_label.place(x=200, y=10)  # Initial position at the top of the right panel

        play_button_image = tk.PhotoImage(file=pathlib.PureWindowsPath(self.resource_path('Data/Play.png')).as_posix())
        play_button = tk.Button(new_window, image=play_button_image, command=play_cue)
        play_button.place(x=175, y=700)  # Initial position at the top of the right panel
        
        cue_type_text = tk.Label(cue_info, text="Cue Type", bg="white", fg="black", relief=tk.SOLID)
        cue_type_text.place(x=0, y=0, width=125, height=20)

        cue_title_text = tk.Label(cue_info, text="Cue Name", bg="white", fg="black", relief=tk.SOLID)
        cue_title_text.place(x=120, y=0, width=325, height=20)

        cue_prewait_text = tk.Label(cue_info, text="Pre-Wait", bg="white", fg="black", relief=tk.SOLID)
        cue_prewait_text.place(x=435, y=0, width=125, height=20)

        cue_duration_text = tk.Label(cue_info, text="Duration", bg="white", fg="black", relief=tk.SOLID)
        cue_duration_text.place(x=555, y=0, width=125, height=20)

        cue_postwait_text = tk.Label(cue_info, text="Post-Wait", bg="white", fg="black", relief=tk.SOLID)
        cue_postwait_text.place(x=675, y=0, width=125, height=20)

        canvas.create_window((0, 80), window=cue_info, anchor="nw")

        cue_lists_button = tk.Button(new_window, text="Cue Lists", bg="gray10", fg="white", font=helv36, relief=tk.SOLID, highlightthickness = 0, bd = 0, activebackground="gray10")
        cue_lists_button.place(x=805, y=5, width=190, height=50)

        script_button = tk.Button(new_window, text="Script/Notes", bg="gray25", fg="white", font=helv36, relief=tk.SOLID, highlightthickness = 2, bd = 2, activebackground="gray25")
        script_button.place(x=975, y=5, width=190, height=50)

        control_button = tk.Button(new_window, text="Control", bg="gray25", fg="white", font=helv36, relief=tk.SOLID, highlightthickness = 2, bd = 2, activebackground="gray25")
        control_button.place(x=1160, y=5, width=190, height=50)

        effects_button = tk.Button(new_window, text="Effects", bg="gray25", fg="white", font=helv36, relief=tk.SOLID, highlightthickness = 2, bd = 2, activebackground="gray25")
        effects_button.place(x=1345, y=5, width=190, height=50)

        # Resizable separator (initially placed at x=800)
        separator = canvas.create_line(800, 0, 800, 800, width=5, fill="white", smooth=True)

        # Minimum width for the left panel
        min_left_panel_width = 500

        right_frame = tk.Frame(canvas, bg="gray10", width=740, height=800)
        right_frame.place(x=canvas.coords(separator)[0], y=200)

        def script_canvas():
            if self.control_scroll is not None:
                self.control_scroll.pack_forget() 
                self.control_scroll_y.pack_forget()
                if self.light_frame is not None:
                    self.light_frame.destroy()
                self.control_scroll = None
                self.control_scroll_y = None
                self.light_frame = None
                
            canvas.create_window((canvas.coords(separator)[0], 100), window=right_frame, anchor="nw")

            # Scrollable Canvas within the right panel
            self.script_scroll = tk.Canvas(right_frame, width=(new_window.winfo_width() - canvas.coords(separator)[0])*0.975, height=670, bg="gray40")
            self.script_scroll.pack(side="left", fill="both", expand=True)
    
            self.script_scroll_y = tk.Scrollbar(right_frame, orient="vertical", command=self.script_scroll.yview)
            self.script_scroll_y.pack(side="right", fill="y")
    
            self.script_scroll.config(yscrollcommand=self.script_scroll_y.set)
    
            # Create a frame within the scrollable canvas to hold cue buttons
            script_scrollable_frame = tk.Frame(self.script_scroll)
            self.script_scroll.create_window((0, 0), window=script_scrollable_frame, anchor="nw")

            return self.script_scroll

        def control_canvas():
            if self.script_scroll is not None:
                self.script_scroll.pack_forget() 
                self.script_scroll_y.pack_forget()
                self.script_scroll = None
                self.script_scroll_y = None
            script_canvas()
            if self.script_scroll is not None:
                self.script_scroll.pack_forget() 
                self.script_scroll_y.pack_forget()
                self.script_scroll = None
                self.script_scroll_y = None
                
            canvas.create_window((canvas.coords(separator)[0], 60), window=right_frame, anchor="nw")

            # Scrollable Canvas within the right panel
            self.control_scroll = tk.Canvas(right_frame, width=(new_window.winfo_width() - canvas.coords(separator)[0])*0.975, height=710, bg="gray15")
            self.control_scroll.pack(side="left", fill="both", expand=True)
    
            self.control_scroll_y = tk.Scrollbar(right_frame, orient="vertical", command=self.control_scroll.yview)
            self.control_scroll_y.pack(side="right", fill="y")
    
            self.control_scroll.config(yscrollcommand=self.control_scroll_y.set)
    
            # Create a frame within the scrollable canvas to hold cue buttons
            control_scrollable_frame = tk.Frame(self.control_scroll)
            self.control_scroll.create_window((0, 0), window=control_scrollable_frame, anchor="nw")

            if self.selected_cue is not None:
                if self.selected_cue.cget("text")[:15].strip() == "Light":
                    self.control_scroll.config(height=300)
                    self.light_control_scroll = light_control_canvas()

            return self.control_scroll

        
        def light_control_canvas():
            self.light_y_position = 0

            if len(self.lights) > 0:
                for button in self.lights:
                    button.destroy()

            self.selected_light = None
            self.last_clicked_light = None
            self.lights = []
            self.light_types = []
            self.light_addresses = []
            
            self.light_frame = tk.Frame(canvas, bg="gray10", width=740, height=800)
            self.light_frame.place(x=canvas.coords(separator)[0], y=200)
                
            canvas.create_window((canvas.coords(separator)[0], 370), window=self.light_frame, anchor="nw")

            # Scrollable Canvas within the right panel
            self.light_control_scroll = tk.Canvas(self.light_frame, width=(new_window.winfo_width() - canvas.coords(separator)[0])*0.975, height=400, bg="black")
            self.light_control_scroll.pack(side="left", fill="both", expand=True)
    
            self.light_control_scroll_y = tk.Scrollbar(self.light_frame, orient="vertical", command=self.light_control_scroll.yview)
            self.light_control_scroll_y.pack(side="right", fill="y")
    
            self.light_control_scroll.config(yscrollcommand=self.light_control_scroll_y.set)
    
            # Create a frame within the scrollable canvas to hold cue buttons
            light_control_scrollable_frame = tk.Frame(self.light_control_scroll)
            self.light_control_scroll.create_window((0, 0), window=light_control_scrollable_frame, anchor="nw")

            active_light_patch_file = open(self.dmx_patch_dir)
            active_light_patch_data = json.load(active_light_patch_file)


            for light in active_light_patch_data["Name"]:
                self.light_y_position += 1
            
                button = tk.Button(self.control_scroll, text=light, bg="gray25", fg="white", compound="left", width=400, height=2, anchor="w")

                def on_click_light(button, light_name):
                    if self.last_clicked_light is not None:
                        self.last_clicked_light.config(bg="gray25", fg="white")
                
                    # Change the current button's color to white
                    button.config(bg="white", fg="black")
    
                    self.selected_light = button
#                    self.light_button = button

                    self.light_button = self.selected_light

                    helv365 = font.Font(family='Helvetica', size=12)
                    
                    self.light_dashboard = True
                    update_color()
                        
    
                    self.last_clicked_light = self.light_button
                
                button.config(command=lambda button=button, light_name=light: on_click_light(button, light_name))
                button.grid(row=self.light_y_position, column=0, sticky="w", pady=0)

                self.lights.append(button)
                self.light_names.append(light)
                self.light_types.append(active_light_patch_data["Output"][active_light_patch_data["Name"].index(light)])
                self.light_addresses.append(active_light_patch_data["Address"][active_light_patch_data["Name"].index(light)])

                print(self.light_types)

                #set scroll region
                scrollable_frame.update_idletasks()
                self.light_control_scroll.config(scrollregion=self.light_control_scroll.bbox("all"))

#                self.light_control = LightControl(self.selected_cue, self.cues, self.lights, 
 #                                                 self.light_types, self.light_addresses, 
  #                                                self.light_dashboard, self.light_button, 
   #                                               self.color_wheel_canvas, self.color_image, self.cue_duration)


            return self.light_control_scroll
            

        
        def update_button_colors(clicked_button):
            buttons = [cue_lists_button, script_button, control_button, effects_button]
            for button in buttons:
                if button == clicked_button:
                    button.config(bg="gray10", highlightthickness = 0, bd = 0, activebackground="gray10")
                    if button == script_button and self.script_scroll is None:
                        print("script")
                        self.script_scroll = script_canvas()
                    elif button == control_button and self.control_scroll is None:
                        print("control")
                        self.control_scroll = control_canvas()
                else:
                    button.config(bg="gray25", highlightthickness = 2, bd = 2, activebackground="gray25")

        # Add button click event handlers
        cue_lists_button.config(command=lambda: update_button_colors(cue_lists_button))
        script_button.config(command=lambda: update_button_colors(script_button))
        control_button.config(command=lambda: update_button_colors(control_button))
        effects_button.config(command=lambda: update_button_colors(effects_button))
        

        def on_drag(event):
            # Calculate new x-position of the separator while dragging
            new_x = event.x
            # Ensure the separator stays within bounds and does not overlap the panels
            if new_x > min_left_panel_width and new_x < new_window.winfo_width() - 718:
                # Move the separator
                canvas.coords(separator, new_x, 0, new_x, 800)

                # Resize the left panel
                canvas.coords(panel_left, 0, 0, new_x, 800)

                # The right panel stays fixed, no need to adjust its coordinates
                canvas.coords(panel_right, new_x, 0, new_window.winfo_width(), 800)

                # Update cue list and cue buttons when resizing
                update_positions()

                # Resize the scrollable canvas to expand from the left
                update_scrollable_canvas(new_x)

                update_cue_length(new_x)

                update_cue_info_length(new_x)

                update_cue_details_length(new_x)

        def on_enter_separator(event):
            new_window.config(cursor="crosshair")  # Change cursor when hovering over separator

        def on_leave_separator(event):
            new_window.config(cursor="arrow")  # Revert to arrow cursor when leaving separator

        # Bind mouse dragging event for resizing
        canvas.tag_bind(separator, "<B1-Motion>", on_drag)

        # Bind enter and leave events to change the cursor
        canvas.tag_bind(separator, "<Enter>", on_enter_separator)
        canvas.tag_bind(separator, "<Leave>", on_leave_separator)

        # Scrollable frame inside the right panel
#        right_frame = tk.Frame(canvas, bg="gray", width=800, height=800)
 #       right_frame.place(x=800, y=0)

        left_frame = tk.Frame(canvas, bg="black", width=800, height=800)
        left_frame.place(x=0, y=0)

        canvas.create_window((0, 100), window=left_frame, anchor="nw")

        # Scrollable Canvas within the right panel
        canvas_scroll = tk.Canvas(left_frame, width=705, height=425, bg="gray10")
        canvas_scroll.pack(side="left", fill="both", expand=True)

        scroll_y = tk.Scrollbar(left_frame, orient="vertical", command=canvas_scroll.yview)
        scroll_y.pack(side="right", fill="y")

        canvas_scroll.config(yscrollcommand=scroll_y.set)

        # Create a frame within the scrollable canvas to hold cue buttons
        scrollable_frame = tk.Frame(canvas_scroll)
        canvas_scroll.create_window((0, 0), window=scrollable_frame, anchor="nw")


        # Update the scroll region of the canvas
        def update_scroll_region():
            scrollable_frame.update_idletasks()
            canvas_scroll.config(scrollregion=canvas_scroll.bbox("all"))

        # Store cues in a list
        y_position = 0  # Initial vertical position for the first button

        def show_context_menu(event, button):
            # Create the context menu
            context_menu = tk.Menu(button, tearoff=0)
            context_menu.add_command(label="Delete", command=lambda: delete_cue_button(button))
            context_menu.post(event.x_root, event.y_root)  # Show the menu at the cursor position

        def delete_cue_button(button):
        
            # Find the index of the button to be deleted
            index = self.cues.index(button)
        
            # Remove the button from the cues list
            self.cue_vals.remove(self.cue_vals[self.cues.index(button)])
            self.cues.remove(button)
            self.cue_durations.remove(self.cue_durations[self.cues.index(button)])

            self.last_clicked_button = None
        
            # Destroy the button widget
            button.destroy()
        
            # Shift the other buttons up by one
            for i in range(index, len(self.cues)):
                # Reposition each button to fill the gap
                self.cues[i].grid_configure(row=i)  # Move the buttons up by 1 position
        
            # Update the scroll region after deletion
            update_scroll_region()

        def light_control():
            if self.control_scroll is None:
                canvas.create_window((canvas.coords(separator)[0], 60), window=right_frame, anchor="nw")
    
                # Scrollable Canvas within the right panel
                self.control_scroll = tk.Canvas(right_frame, width=(new_window.winfo_width() - canvas.coords(separator)[0])*0.975, height=710, bg="gray15")
                self.control_scroll.pack(side="left", fill="both", expand=True)
        
                self.control_scroll_y = tk.Scrollbar(right_frame, orient="vertical", command=self.control_scroll.yview)
                self.control_scroll_y.pack(side="right", fill="y")
        
                self.control_scroll.config(yscrollcommand=self.control_scroll_y.set)
        
                # Create a frame within the scrollable canvas to hold cue buttons
                control_scrollable_frame = tk.Frame(self.control_scroll)
                self.control_scroll.create_window((0, 0), window=control_scrollable_frame, anchor="nw")
                
            self.control_scroll.config(height=300)
            self.light_control_scroll = light_control_canvas()


        
        def add_cue_button(window, cue_type):
            nonlocal y_position
        
            # Create the cue button
            left_panel_width = int(new_window.winfo_width() - canvas.coords(separator)[0])
        
            if cue_type == "Light":
                button = tk.Button(scrollable_frame, text=cue_type, fg="white", bg="navy", compound="left", width=left_panel_width, height=2, anchor="w")
            if self.is_new_workspace is False:
                button.config(text=self.cue_text[self.cue_load_number])
            elif self.is_new_workspace is True:
                button.config(text="Light" + (" "*30) + "New Cue" + (" "*140) + "00:05:00")
                
            button.grid(row=y_position, column=0, sticky="w", pady=0)  # Position the button in grid layout

            active_light_patch_file = open(self.dmx_patch_dir)
            active_light_patch_data = json.load(active_light_patch_file)

            self.cues.append(button)
            self.cue_durations.append(5)
    
            self.cue_vals.append([])
    
            for n in range(len(active_light_patch_data["Name"])):
                self.cue_vals[self.cues.index(button)].append([])
    
            print("Nonsense: ", self.cue_vals)
            print("Lights Length: ", len(active_light_patch_data["Name"]))

        
            # Update the y_position for the next button (add 1 for each new button in grid)
            y_position += 1
        
            # Update the scroll region to make sure the scroll works
            update_scroll_region()
        
            # Bind right-click event to show context menu
            button.bind("<Button-3>", lambda event: show_context_menu(event, button))

                
        
            # Add left-click event for selecting the button
            def on_click(event):

                button._drag_data = {'x': event.x, 'y': event.y}

                current_cue_type = button.cget("text")[:15].strip()
    
                if self.control_scroll is not None and current_cue_type == "Light":
                    print("Light Control")
                    if self.control_scroll is not None:
                        self.control_scroll.pack_forget() 
                        self.control_scroll_y.pack_forget()
                        if self.light_frame is not None:
                            self.light_frame.destroy()
                        self.control_scroll = None
                        self.control_scroll_y = None
                        self.light_frame = None
                    script_canvas()
                    if self.script_scroll is not None:
                        self.script_scroll.pack_forget() 
                        self.script_scroll_y.pack_forget()
                        self.script_scroll = None
                        self.script_scroll_y = None
#                    control_canvas()
                    light_control()
                    
                
                # Reset the last clicked button to its original color
                if self.last_clicked_button is not None:
                    cue_type = self.last_clicked_button.cget("text")[:15].strip()
                    if cue_type == "Light":
                        self.last_clicked_button.config(bg="navy", fg="white")
        
                # Change the current button's color to white
                button.config(bg="white", fg="black")
                
                # Update the last clicked button
                self.last_clicked_button = button
        
                # Handle cue details and display in text box (as before)
                self.selected_cue = button
                cue_title_label = tk.Label(cue_details, text="Name", bg="gray10", fg="white", font=helv362, relief=tk.SOLID, borderwidth=0)
                cue_title_label.place(x=0, y=10, width=80, height=20)
        
                cue_title_box = tk.Text(cue_details, height=1, width=50)
                cue_title_box.place(x=70, y=10)
        
                cue_title_box.insert("1.0", (((self.selected_cue.cget("text")[10:].strip()).split(":")[0])[:-2]).strip())

                cue_duration_label = tk.Label(cue_details, text="Duration", bg="gray10", fg="white", font=helv362, relief=tk.SOLID, borderwidth=0)
                cue_duration_label.place(x=0, y=50, width=80, height=20)
        
                cue_duration_box = tk.Text(cue_details, height=1, width=10)
                cue_duration_box.place(x=70, y=50)

                index = self.selected_cue.cget("text").find((((self.selected_cue.cget("text")[10:].strip()).split(":")[0])[:-2]).strip())
                cue_duration_text = (self.selected_cue.cget("text")[index + len((((self.selected_cue.cget("text")[10:].strip()).split(":")[0])[:-2]).strip()):]).strip()
        
                cue_duration_box.insert("1.0", cue_duration_text)
                
                cue_title_box.bind("<Return>", lambda event: exit_textbox(event, cue_title_box, cue_duration_box))
                cue_duration_box.bind("<Return>", lambda event: exit_duration_textbox(event, cue_duration_box, cue_title_box, self.cues.index(button)))
        
            button.bind("<Button-1>", on_click)

            
            def on_button_drag_move(event):
                button.lift()
                # Calculate the distance moved
                dx = event.x - button._drag_data['x']
                dy = event.y - button._drag_data['y']
                
                # Move the button
#                new_x = button.winfo_x() + dx
                new_y = button.winfo_y() + dy
                button.place(x=0, y=new_y)
                
                # Update the drag data
                button._drag_data['x'] = event.x
                button._drag_data['y'] = event.y
            
            def on_button_drop(event):
                # Calculate the final position where the button is dropped
                new_y_position = event.y  # Get the Y position where the button is dropped
                
                # Update the button's position in the layout
                button.place(x=button.winfo_x(), y=new_y_position)
                
                # Reorder buttons based on their new Y position
                reorder_cue_buttons()
        
            def reorder_cue_buttons():
                # Sort the buttons based on their new Y position and reorder them
                sorted_cues = sorted(self.cues, key=lambda b: b.winfo_y())
                
                # Reposition the buttons in sorted order
                for idx, cue in enumerate(sorted_cues):
                    cue.grid(row=idx, column=0, sticky="w")
                
                # Update the list of cues to reflect the new order
                self.cues = sorted_cues

                print(self.cue_vals)
                self.cue_vals = [self.cue_vals[self.cues.index(cue)] for cue in sorted_cues]

                self.cue_durations = [self.cue_durations[self.cues.index(cue)] for cue in sorted_cues]
        
            # Bind the drag and drop events
#            button.bind("<ButtonPress-1>", on_button_drag_start)
            button.bind("<B1-Motion>", on_button_drag_move)
            button.bind("<ButtonRelease-1>", on_button_drop)

        if self.is_new_workspace is False and len(self.cue_text) > 0:
            for i in range(len(self.cue_text)):
                self.cue_load_number = i
                add_cue_button(new_window, "Light")

        # Update positions of all cue buttons (for resizing the window)
        def update_positions():
            # Get the current position of the separator (this gives us the left panel's x-coordinate)
            separator_x = canvas.coords(separator)[0]

            # Recalculate the left panel's width based on separator position
            left_panel_width = separator_x  # The left panel's width is from window edge to separator

            # Adjust the x position of the cue list (center it in the right panel)
#            cue_list_label.place(x=(separator_x + (panel_right - cue_list_label.winfo_width() - 800) / 2))

 #           play_button.place(x=(separator_x + (panel_right - play_button.winfo_width() - 750) / 2))

            cue_list_label.place(x=separator_x - (left_panel_width - cue_list_label.winfo_width() + 775) / 2)

            play_button.place(x=separator_x - (left_panel_width - play_button.winfo_width() + 1030) / 2)

            cue_lists_button.place(x=separator_x - (left_panel_width - play_button.winfo_width() - 300) / 2)
            script_button.place(x=separator_x - (left_panel_width - play_button.winfo_width() - 650) / 2)
            control_button.place(x=separator_x - (left_panel_width - play_button.winfo_width() - 1000) / 2)
            effects_button.place(x=separator_x - (left_panel_width - play_button.winfo_width() - 1350) / 2)

#            if self.light_frame is not None:
 #               self.light_frame.config(width=new_window.winfo_width() - separator_x)


            # Update the position of each cue button
#            for i, button in enumerate(cues):
 #               # Recalculate positions based on some logic
  #              button.grid(row=i, column=0, sticky="w", pady=0)  # Adjust this as needed for your layout

        # Function to update the scrollable canvas width
        def update_scrollable_canvas(separator_x):
            left_panel_width = new_window.winfo_width() - separator_x  # Right panel width
            canvas_scroll.config(width=1520-left_panel_width)  # Adjust for the scrollbar width
            if self.script_scroll is not None:
                self.script_scroll.config(width=left_panel_width * 0.975)
                right_frame.place(x=separator_x, y=100)
#                self.script_scroll.place(x=separator_x)
                print("Test")
            if self.control_scroll is not None:
                self.control_scroll.config(width=left_panel_width * 0.975)
                right_frame.place(x=separator_x, y=60)

        def update_cue_length(separator_x):
            left_panel_width = new_window.winfo_width() - separator_x

            for i, button in enumerate(self.cues):
                button.config(width=1520-left_panel_width)

        def update_cue_info_length(separator_x):
            left_panel_width = new_window.winfo_width() - separator_x
            cue_info.config(width=1520-left_panel_width)

        def update_cue_details_length(separator_x):
            left_panel_width = new_window.winfo_width() - separator_x
            cue_details.config(width=1520-left_panel_width)

        # Call the update function when the window is resized
        new_window.bind("<Configure>", lambda event: update_positions())

        update_scroll_region()
        update_scrollable_canvas(800)  # Initial separator position

        def update_color():

            def clear_all():
                try:
                    self.dmx = DMXConnection(usb_port)
                except:
                    print("No DMX Device")

                if self.dmx is not None:               
                    for n in range(len(self.light_names)):
                        start_str, end_str = self.light_addresses[n].split('-')
                        start = int(start_str)
                        end = int(end_str)
    
                        print("Clearing Lights")
    
                        self.dmx.set_channel(int(list(range(start, end + 1))[0])-1, 0)
                        self.dmx.set_channel(int(list(range(start, end + 1))[1])-1, 0)
                        self.dmx.set_channel(int(list(range(start, end + 1))[2])-1, 0)
                        
                    self.dmx.render()

            if self.light_dashboard == True:
    
                try:
                    color_wheel_path = pathlib.PureWindowsPath(self.resource_path("Data/Color Wheel(3).png")).as_posix()  # Replace with your image path
                    self.color_image = Image.open(color_wheel_path).convert("RGB")
                    color_wheel_image = ImageTk.PhotoImage(self.color_image)

                except FileNotFoundError:
                    print(f"Error: Color wheel image '{color_wheel_path}' not found.")
                    exit()
                        
                # Create a Canvas to display the image in the main window
                self.color_wheel_canvas = tk.Canvas(self.light_control_scroll, width=self.color_image.width, height=self.color_image.height, highlightthickness=0)
                self.color_wheel_canvas.create_image(0, 0, anchor=tk.NW, image=color_wheel_image)
                self.color_wheel_canvas.place(x=160, y=5)
                        
                # Circle properties for the cursor
                circle_radius = 8
                cursor_circle = self.color_wheel_canvas.create_oval(0, 0, 0, 0, outline="white", width=3)  # Initial position (0, 0)
                        
                        
                # Create a frame for the brightness scale
                frame = tk.Frame(self.light_control_scroll, bg="black", padx=10, pady=10)
                frame.place(x=5, y=5)
                        
                helv364 = font.Font(family='Helvetica', size=12)

#                self.light_control = LightControl(self.selected_cue, self.cues, self.lights, self.light_types, 
 #                                                 self.light_addresses, self.light_dashboard, self.light_button, 
  #                                                self.color_wheel_canvas, self.color_image, self.cue_duration)

                # Bind mouse motion event to show the color preview as the user moves the mouse
                self.color_wheel_canvas.bind("<Motion>", self.show_color)
                self.color_wheel_canvas.bind("<Button-1>", self.pick_color)  # Bind mouse click event to pick color
                        
                # Brightness adjustment scale
                self.brightness_scale = tk.Scale(frame, from_=0, to=100, orient=tk.VERTICAL, sliderlength=30, length=370,
                                                        bg="black", fg="white", highlightbackground="black", highlightcolor="white",
                                                        activebackground="white", troughcolor="white",
                                                        label="Intensity   ", font=helv364, command=lambda value: self.update_color_wheel(int(value) / 100))
                self.brightness_scale.set(100)  # Set initial brightness to 100%
                self.brightness_scale.pack()

                        
                # Initial image update to apply the default brightness
                self.update_color_wheel(1)
                            
    #            light_color = color_picker(self.light_control_scroll)
                helv365 = font.Font(family='Helvetica', size=12)
                clear_all_button = tk.Button(self.light_control_scroll, text="Clear All", font=helv365, bg="gray25", fg="white")
                clear_all_button.place(x=595, y=50)
                clear_all_button.config(width=10)
                clear_all_button.config(command=clear_all)

                update_selected_cue_button = tk.Button(self.light_control_scroll, text="Update Cue", font=helv365, bg="gray25", fg="white")
                update_selected_cue_button.place(x=595, y=125)
                update_selected_cue_button.config(width=10)
                update_selected_cue_button.config(command=lambda : print("Update"))
                        
                start_str, end_str = self.light_addresses[self.lights.index(self.light_button)].split('-')
                start = int(start_str)
                end = int(end_str)
                
                print(self.light_color)

        usb_port = self.find_usb_serial_port()

        try:
            self.dmx = DMXConnection(usb_port)
        except:
            messagebox.showerror("USB Device Not Found", "Check to ensure that your USB device is plugged into your computer.")

        icon_path = pathlib.PureWindowsPath(self.resource_path("Data/ShowSpace_Logo.ico")).as_posix()
        new_window.iconbitmap(icon_path)

        new_window.mainloop()


if __name__ == '__main__':
    appdata_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "ShowSpace")
    
    if os.path.exists(appdata_dir):
        print("ShowSpace Folder Exists")
        json_path = os.path.join(appdata_dir, "active_dmx_patch.json")

        if os.path.exists(json_path):
            print("Active DMX Patch Exists")
        else:
            data = {
                "Name": [],
                "Address": [],
                "Output": []
            }
        
            json_path = os.path.join(appdata_dir, "active_dmx_patch.json")
            with open(json_path, "w") as file:
                json.dump(data, file, indent=6)
            
    else:
        os.makedirs(appdata_dir, exist_ok=True)
        json_path = os.path.join(appdata_dir, "active_dmx_patch.json")

        data = {
            "Name": [],
            "Address": [],
            "Output": []
        }
        
        json_path = os.path.join(appdata_dir, "active_dmx_patch.json")
        with open(json_path, "w") as file:
            json.dump(data, file, indent=6)

    app = StartWindow()
    app.open()

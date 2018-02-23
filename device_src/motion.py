###
 # Copyright 2017, Google, Inc.
 # Licensed under the Apache License, Version 2.0 (the `License`);
 # you may not use this file except in compliance with the License.
 # You may obtain a copy of the License at
 # 
 #    http://www.apache.org/licenses/LICENSE-2.0
 # 
 # Unless required by applicable law or agreed to in writing, software
 # distributed under the License is distributed on an `AS IS` BASIS,
 # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 # See the License for the specific language governing permissions and
 # limitations under the License.
###

import RPi.GPIO as GPIO
import pyrebase
import time
import os
from datetime import datetime
import sys

api_key = "<firebase_api_key>"
firebase_user = "<firebase_user>" # Requires write access to firebase
firebase_pw = "<firebase_password>"
firebase_domain = "<firebase_domain>"
device_id = "<allows for multiple devices>"
database_url = "<firebase_database_url>"
storage_bucket = "<cloud_storage_bucket_url>"
service_account_file = "<path_to_service_json_on_disk>"

gpio_pir_in = 13; # Should be pin connected to data pin on PIR sensor
gpio_led_pin = 40; # Should be the power pin for LED

config = {
	"apiKey": api_key,
	"authDomain": firebase_domain,
	"databaseURL": database_url,
	"storageBucket": storage_bucket,
	"serviceAccount": service_account_file
}

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(gpio_pir_in, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(gpio_led_pin, GPIO.OUT)

current_time = 0
current_motion = 0
repeat_time = 0
needs_updating = 0

while True:
	i = GPIO.input(gpio_pir_in)
	motion = 0
	if i == 1:
		motion = 1

	# Need a chunk of code to account for a weirdness of the PIR
	# sensor. No matter what I've tried, I'm getting a blip of motion
	# every minute like clockwork. The internet claims everything from
	# jumper position (H v. L), power fluctations, etc. Nothing offered
	# seems to work, so I'm falling back on a software solution to
	# discount the minute blip

	current_time = int(round(time.time()))
	formatted_time = datetime.fromtimestamp(current_time).ctime()
	if motion:
		print ("I have motion")
		print (" My repeat time is: {}".format(datetime.fromtimestamp(repeat_time).ctime()))
		if repeat_time == 0:
			repeat_time = current_time
			print("  First time for repeat: {}\n".format(formatted_time))
		elif current_time >= repeat_time + 55 and current_time <= repeat_time + 65:
			print ("  Repeat time: {}\n".format(formatted_time))
			needs_updating = 1
			time.sleep(1.0)
			continue
		else:
			print ("  Real motion: {}\n".format(formatted_time))
			repeat_time = current_time
	elif needs_updating:
		needs_updating = 0
		repeat_time += 60
	else:
		if current_time > repeat_time + 90:
			print ("No motion, but updating repeat time\nUpdating to: {}\n".format(datetime.fromtimestamp(repeat_time + 60).ctime()))
			repeat_time += 60

		# Turn on/off the LED based on motion
	GPIO.output(40, motion)

		# If the current motion is the same as the previous motion,
		# then don't send anything to firebase. We only track changes.
	if current_motion == motion:
		time.sleep(1.0)
		continue

        previous_motion = current_motion
	current_motion = motion

	try:
		firebase = pyrebase.initialize_app(config)
		db = firebase.database()
		if motion == 1:
			db.child("latest_motion").set('{{"ts": {} }}'.format(current_time))
		db.child(firebase_column).push('{{"ts": {}, "device_id": {}}, "motion": {} }}'.format(current_time, device_id, motion))
	except:
		e = sys.exc_info()[0]
		print ("An error occurred: {}".format(e))
		# If we've hit an exception, we want to reset the motion so that we catch a case
		# where a stop in motion might get missed, and we'd get stuck in a loop where
		# we think we're still moving even though we're not, and it wouldn't get fixed
		# until motion triggers again, which might be a long time later
		current_motion = previous_motion

	time.sleep(1.0)


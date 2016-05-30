#!/usr/bin/python

import json
import logging
import sys
import requests
import requests.packages.urllib3
from datetime import timedelta, datetime, tzinfo
import dateutil.parser 
from dateutil.relativedelta import *
from dateutil.tz import *
from base64 import encodestring
import uuid

class csaservice :

	def __init__(self, config=None, order=None) :

		self.order = order
		self.config = config

		self.session = requests.Session()
		self.session.url = 'https://' + self.config['host']
		self.auth = encodestring(self.config['apiusername']+ ":" +self.config['apipassword'])
		self.session.headers.update({'Authorization': 'Basic '+self.auth.rstrip()})
		self.session.headers.update({'Accept':'application/json'})

		self.error = None
		self.token = None
		self.token_expires = None
		self.subscription_id = None
		self.subscription_name = None
		self.service_id = None
		self.fields = None
		self.start_date = None
		self.catalog_id = None

		if self.config['trustcert'] is True :
			requests.packages.urllib3.disable_warnings() 

	def subscribe(self) :

		self._verify_token()
		self._get_offer()
		self._set_order_fields()

		params = {}
		params['catalogId'] = self.offer['catalogId']

		url = self.session.url +'/csa/api/mpp/mpp-request/'+self.offer['id']

		self.start_date = datetime.utcnow().isoformat()[:-3]+'-00:00'

		payload = {}
		payload['action'] = "ORDER"
		payload['categoryName'] = self.offer['category']['name']
		payload['subscriptionName'] = self.order['subscriptionPrefix'] + self._uuid()
		payload['subscriptionDescription'] = payload['subscriptionName']
		payload['startDate'] =  self.start_date
		payload['fields'] = self.fields

		logging.info("Order service %s", payload['subscriptionName'])

		files = {'requestForm': ('', json.dumps(payload), 'application/json')}

		self.session.headers.update({'X-Auth-Token': self.token})

		logging.info('Submit request %s', payload['subscriptionName'])
		result = self.session.post(url, params=params, files=files, verify=False)

		logging.debug(result.request.headers)
		logging.debug(result.request.body)
		logging.debug(result.text)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = result.reason

		self.request =  json.loads(result.text)
		self.subscription_name = payload['subscriptionName']
		return self.subscription_name

	def cancel(self, subscription_id = None) :

		if subscription_id is not None :
			self.subscription_id = subscription_id

		if self.subscription_id is None:
			return False

		if self.catalog_id is None:
			self._get_subscription(self.subscription_id)

		logging.info("Canceling service %s", self.subscription_name)

		self._verify_token()

		url = self.session.url + "/csa/api/mpp/mpp-request/" + self.subscription_id

		postdata = {}
		postdata['action'] = 'CANCEL_SUBSCRIPTION'

		params = {}
		params['catalogId'] = self.catalog_id

		files = {'requestForm': ('', json.dumps(postdata), 'application/json')}

		self.session.headers.update({'X-Auth-Token': self.token})
		result = self.session.post(url, params=params, files=files, verify=False)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = result.reason

		logging.debug(result.text)

	def delete(self, subscription_id = None) :

		if subscription_id is not None :
			self.subscription_id = subscription_id

		if self.subscription_id is None:
			return False

		if self.catalog_id is None:
			self._get_subscription(self.subscription_id)

		logging.info('Delete subscription %s', self.subscription_name)

		self._verify_token()

		url = self.session.url + "/csa/api/mpp/mpp-subscription/" + self.subscription_id

		self.session.headers.update({'X-Auth-Token': self.token})
		result = self.session.delete(url, verify = False)

		logging.debug(result.request.headers)
		logging.debug(result.request.body)
		logging.debug(result.text)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = result.reason
			return False

		return True

	def get_subscription_status(self, name = None) :
		logging.info("Get Service Status")

		self._verify_token()
		
		url = self.session.url + '/csa/api/mpp/mpp-subscription/filter'

		if name is not None :
			self.subscription_name = name

		postdata = {}
		postdata['name'] = self.subscription_name

		self.session.headers.update({'X-Auth-Token': self.token})
		result = self.session.post(url, json=postdata, verify = False)

		logging.debug(result.request.headers)
		logging.debug(result.request.body)
		logging.debug(result.text)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = 'Cannot get subscription status'
			return

		subscription = json.loads(result.text)
		self.subscription = subscription

		for i in subscription['members'] :
			if i['name'] == self.subscription_name :
				self.status = i['status']
				self.subscription_id = i['id']
				self.catalog_id = i['catalogId']
				return self.status
	
	def get_instance_details(self, name = None) :
		
		if name is not None :
			self.subscription_name = name

		logging.info("Get service details")

		self._verify_token()

		url = self.session.url + "/csa/api/mpp/mpp-instance/filter"
		
		postdata = {}
		postdata['name'] = self.subscription_name

		self.session.headers.update({'X-Auth-Token': self.token})
		result = self.session.post(url, json=postdata, verify = False)

		logging.debug(result.request.headers)
		logging.debug(result.request.body)
		logging.debug(result.text)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = 'Cannot get service instance'
			return

		instance = json.loads(result.text)
		members_count = len(instance['members'])

		if members_count != 1 :
			logging.error('The result is gt or lt than 1')
			return

		for i in instance['members'] :
			if i['name'] == self.subscription_name:
				self.service_id = i['id']
				self.catalog_id = i['catalogId']

		url = self.session.url + "/csa/api/mpp/mpp-instance/"+self.service_id
		
		params = {}
		params['catalogId'] = self.catalog_id

		self.session.headers.update({'X-Auth-Token': self.token})
		result = self.session.get(url, verify=False, params=params)

		logging.debug(result.request.headers)
		logging.debug(result.request.body)
		logging.debug(result.text)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = 'Cannot get service instance details'
			return

		instance = json.loads(result.text)
		self.service_id = instance['id']

		return instance	
	
	def get_token(self) :
		self._verify_token()
		return self.token

	def get_subscription(self, subscription_id = None):
		self._get_subscription(subscription_id)

	def _get_token(self) :

		logging.info("Get auth token")

		url = self.session.url + '/idm-service/v2.0/tokens'

		postdata = {}
		postdata['passwordCredentials'] = self.config['credentials']
		postdata['tenantName'] = self.config['tenantName']
	
		result = self.session.post(url, json=postdata, verify=False)

		logging.debug(result.request.headers)
		logging.debug(result.request.body)
		logging.debug(result.text)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			sys.exit(2)

		
		self.token = json.loads(result.text)['token']['id']
		self.token_expires = json.loads(result.text)['token']['expires']
	
	def _get_offer(self) :
		
		logging.info("Get Offering Ids")

		self._verify_token()

		url = self.session.url +'/csa/api/mpp/mpp-offering/filter'

		self.session.headers.update({'X-Auth-Token': self.token})

		postdata = {}
		postdata['name'] = self.order['offeringName']
	
		result = self.session.post(url, json=postdata, verify=False)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = result.reason

		logging.debug(result.text)
	
		o = json.loads(result.text)
	 
	 	oid = o['members'][-1] #set last version as the version

	 	#reset the version if specified in config
		for i in o['members'] :
			if i['offeringVersion'] == self.order['offeringVersion'] :
				oid = i

		logging.info("Get Offer Details")

		params = {}
		params['catalogId'] = oid['catalogId']
		params['category']  = oid['category']['name']
		params['returnDynamicValues'] = 'false'

		url = self.session.url +'/csa/api/mpp/mpp-offering/'+ oid['id']

		self.session.headers.update({'X-Auth-Token': self.token})
		result = self.session.get(url, verify=False, params=params)
		
		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = result.reason

		logging.debug(result.text)
		self.offer = json.loads(result.text)
	
	def _set_order_fields(self) :

		logging.info("Create order fields")

		self._verify_token()

		f = {}

		for i in self.offer['fields'] :
			id = i['id']
			name = i['name']
		
			if name in self.order['serviceOptions'] :
				f[id] = self.order['serviceOptions'][name]
			else :
				if 'value' in i:
					f[id] = i['value']
	
		logging.debug(f)
		self.fields = f

	def _verify_token(self):
		logging.debug('Verify token expiration date')
		
		if self.token is None :
			self._get_token()
			return

		if self.token and self.token_expires :
			now = datetime.now(tzutc())
			exp = dateutil.parser.parse(self.token_expires)
			cur = dateutil.parser.parse(str(now))

			delta = relativedelta(exp, cur)

			logging.debug(delta)

			if delta.hours :
				self._get_token()
				return

			if int(delta.minutes) < 5 :
				self._get_token()
				return

	def _get_subscription(self, subscription_id = None) :

		if subscription_id is not None:
			self.subscription_id = subscription_id

		if self.subscription_id is None:
			self.error = 'missing subscription id'
			logging.error(self.error)
			return
		
		logging.info("Get subscription %s", self.subscription_id)
		
		self._verify_token()

		url = self.session.url + '/csa/api/mpp/mpp-subscription/'+ self.subscription_id

		postadata = {}
		params = {}

		self.session.headers.update({'X-Auth-Token': self.token})
		result = self.session.get(url, params=params, verify = False)

		logging.debug(result.request.headers)
		logging.debug(result.request.body)
		logging.debug(result.text)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = result.reason
			return

		data = json.loads(result.text)
		
		self.subscription_id = data['id']
		self.catalog_id = data['catalogId']
		self.subscription_name = data['name']

		return data

	def _filter_offer(self) :
		
		logging.info("Search Offers")

		self._verify_token()

		url = self.session.url +'/csa/api/mpp/mpp-offering/filter'

		self.session.headers.update({'X-Auth-Token': self.token})

		postdata = {}
		postdata['name'] = self.order['offeringName']
	
		result = self.session.post(url, json=postdata, verify=False)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = result.reason
			return

		logging.debug(result.text)
	
		return json.loads(result.text)

	def _get_offer_stub(self) :
		
		logging.info("Get Offer Information")

		params = {}
		params['catalogId'] = oid['catalogId']
		params['category']  = oid['category']['name']
		params['returnDynamicValues'] = 'false'

		url = self.session.url +'/csa/api/mpp/mpp-offering/'+ oid['id']

		self.session.headers.update({'X-Auth-Token': self.token})
		result = self.session.get(url, verify=False, params=params)
		
		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = result.reason
			return

		logging.debug(result.text)
		self.offer = json.loads(result.text)
		return self.offer
	
	def _uuid(self) :
		return str(uuid.uuid4().get_hex().upper()[0:8])

	def _method_stub(self) :

		logging.info('method stub info')

		url = self.session.url + '@self'

		postadata = {}
		params = {}

		self.session.headers.update({'X-Auth-Token': self.token})
		result = self.session.METHOD(url, json=postdata, verify = False)

		logging.debug(result.request.headers)
		logging.debug(result.request.body)
		logging.debug(result.text)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = 'ERROR REASON'
			return

		return json.loads(result.text)

	def get_request(self) :

		logging.info('Get Request Information')

		url = self.session.url + '/csa/api/mpp/mpp-request/' + self.request['id']
		
		params = {}
		params['catalogId'] = self.offer['catalogId']

		self.session.headers.update({'X-Auth-Token': self.token})
		result = self.session.get(url, params=params, verify = False)

		logging.debug(result.request.headers)
		logging.debug(result.request.body)
		logging.debug(result.text)

		if (result.reason != 'OK') :
			logging.error(result.reason)
			self.error = result.reason
			return

		data = json.loads(result.text)

		if data['subscription']['displayName'] is None:
			self.error = 'Cannot get subscription name'
			logging.error('Cannot get subscription name')
			return False
		else :
			self.subscription_name = data['subscription']['displayName']
			return self.subscription_name

		return json.loads(result.text)

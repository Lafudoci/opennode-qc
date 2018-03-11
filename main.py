<<<<<<< HEAD
import json, requests, time, datetime, os
=======
import json, requests, time, datetime, configparser

config = configparser.ConfigParser()
config.read('config.ini')

zone_id = config['cloudflare-setting']['Zone-id']
cf_auth_email = config['cloudflare-setting']['X-Auth-Email']
cf_auth_key = config['cloudflare-setting']['X-Auth-Key']
cf_record_name = config['cloudflare-setting']['Record-Name']
>>>>>>> 42d4d469050b6a8918bf733be73607dff7496af1

height_range = 5
threshold = 850

xmr_headers = {
	'content-type': 'application/json',
}

url_cf = 'https://api.cloudflare.com/client/v4/zones/'+zone_id+'/dns_records/'
<<<<<<< HEAD
name_cf = 'node.xmr-tw.org'
=======
name_cf = cf_record_name
>>>>>>> 42d4d469050b6a8918bf733be73607dff7496af1
headers_cf = {
	'Content-Type': 'application/json',
	'X-Auth-Email': cf_auth_email,
	'X-Auth-Key': cf_auth_key
}

#calculate health
def measureHealth(obj, his, max):
	score = his * 0.75
	if obj['status'] == 'online':
		if obj['height'] < (max - height_range):
			score += 50
		else:
			score += 150
		score += (3000 - obj['elapsed']) / 30
	return score
def cutPort(str):
	i = str.find(':')
	return str[:i]

while True:
	# Open IP File 
	try:
		ipf = open('IP.in', 'r')
		xmr_nodes = json.loads(ipf.read())
		ipf.close()
	except (OSError, IOError) as e:
		print('IP FILE open error\n' + e + '\n')
	
	#Get Height From Node
	node_ary = []
	max_height = -1
	for node_ip in xmr_nodes:
		node_infos = {'IP': node_ip['IP'], 'host': node_ip['host']}
		try:
			start = datetime.datetime.now()
			resp = requests.post(url='http://'+node_ip['IP']+'/getheight', headers=xmr_headers, timeout = 2)
			node_infos['elapsed'] = (datetime.datetime.now() - start).microseconds/1000
			node_json = json.loads(resp.text)
			if node_json['status'] == 'OK':
				node_infos['height'] = node_json['height']
				node_infos['status'] = 'online'
				if node_json['height'] > max_height:
					max_height = node_json['height']
			else:
				node_infos['height'] = -1
				node_infos['status'] = 'offline'
		except requests.exceptions.RequestException as err:
			node_infos['elapsed'] = 3000
			node_infos['height'] = -1
			node_infos['status'] = 'offline'

		node_ary.append(node_infos);
		print(str(node_infos))

	#Open Score File
	try:
		scf = open('web/last.json', 'r')
		history = json.loads(scf.read())
		scf.close()
	except (OSError, IOError) as e:
		print('Histroy FILE open error\n')
		history = []

	for node_obj in node_ary:
		history_score = 500
		for his in history:
			if node_obj['IP'] == his['IP']:
				history_score = his['score']
				break
		node_obj['score'] = measureHealth(node_obj, history_score, max_height)

	#Sort
	node_ary.sort(reverse = True, key = lambda obj:obj['score'])
	#print(str(node_ary))
	scf = open('web/last.json', 'w')
	scf.write(json.dumps(node_ary))
	scf.close()

	scf = open('data/'+datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")+'.json', 'w')
	scf.write(json.dumps(node_ary))
	scf.close()

	#Get DNS List From Cloudflare
	try:
		res_cf = requests.get(url = url_cf, json = {'name': name_cf, 'per_page': 100}, headers = headers_cf)
		json_cf = json.loads(res_cf.text)
		if json_cf['success'] == True:
			print('Success When Get DNS List')
			#Create DNS Record
			for node_obj in node_ary:
				if node_obj['score'] >= threshold and node_obj['status'] == 'online':
					flag_exist = False
					for list_obj in json_cf['result']:
						if list_obj['name'] == name_cf and list_obj['content'] == cutPort(node_obj['IP']):
							flag_exist = True
							break
					if flag_exist:
						print(node_obj['IP'] + ' already exist')
					else:
						try:
							res_create = requests.post(url = url_cf, json = {'name': name_cf, 'type': 'A', 'content': cutPort(node_obj['IP'])}, headers = headers_cf)
							json_create = json.loads(res_create.text)
							if json_create['success'] == True:
								print(node_obj['IP'] + ' create record success')
							else:
								print(node_obj['IP'] + ' create record fail')
								print(res_create.text)
						except requests.exceptions.RequestException as err:
							print(str(err))
			#Delete DNS Record
			for list_obj in json_cf['result']:
				if list_obj['name'] == name_cf:
					flag_exist = False
					for node_obj in node_ary:
						if cutPort(node_obj['IP']) == list_obj['content'] and node_obj['score'] >= threshold and node_obj['status'] == 'online':
							flag_exist = True
							break
					if not flag_exist:
						try:
							res_del = requests.delete(url = url_cf+list_obj['id'], headers = headers_cf)
							json_del = json.loads(res_del.text)
							if json_del['success'] == True:
								print(list_obj['content'] + ' delete record success')
							else:
								print(list_obj['content'] + ' delete record fail')
								print(res_del.text)
						except requests.exceptions.RequestException as err:
							print(str(err))
		else:			
			print('Error When Get DNS List')
	except requests.exceptions.RequestException as err:
		print(str(err))

	#analysis
	names = os.listdir('data/')
	today = datetime.datetime.now().date()
	analysis = []
	for name in names:
		day = datetime.datetime.strptime(name, "%Y-%m-%d %H-%M-%S.json").date()
		diff = today - day
		#print(diff.days)
		if diff.days > 30:
			os.remove('data/'+name)
			continue
		try:
			ipf = open('data/'+name, 'r')
			file_content = json.loads(ipf.read())
			ipf.close()
			#print(file_content)
		except (OSError, IOError) as e:
			print('FILE open error\n' + e + '\n')
		for fip in file_content:
			flag = False
			for fa in analysis:
				if fip['IP'] == fa['IP']:
					flag = True
					fa['count'] += 1
					fa['host'] = fip['host']
					fa['totalscore'] += fip['score']
					fa['totalelapsed'] += fip['elapsed']
					if fa['height'] < fip['height']:
						fa['height'] = fip['height']
					if fip['status'] == 'online':
						fa['totalonline'] += 1
					break
			if flag == False:
				newip = {}
				newip['count'] = 1
				newip['IP'] = fip['IP']
				newip['host'] = fip['host']
				newip['totalscore'] = fip['score']
				newip['totalelapsed'] = fip['elapsed']
				newip['height'] = fip['height']
				if fip['status'] == 'online':
					newip['totalonline'] = 1
				else:
					newip['totalonline'] = 0
				analysis.append(newip)
	#averge
	for node in analysis:
		node['avg_score'] = node['totalscore'] / node['count']
		node['avg_elapsed'] = node['totalelapsed'] / node['count']
		node['online_rate'] = node['totalonline'] / node['count']

	analysis.sort(reverse = True, key = lambda obj:obj['avg_score'])

	scf = open('web/analysis.json', 'w')
	scf.write(json.dumps(analysis))
	scf.close()

	print('Enter Sleep->')
	time.sleep(300)
	print('<-Leave Sleep')




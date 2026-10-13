
import json
import boto3
import psycopg2
import os
import json, time
import mimetypes
from langchain_community.chat_models import BedrockChat
from datetime import datetime, timedelta
import string
import secrets

db_user = os.environ['db_user']
db_password =os.environ['db_password']   
db_host =os.environ['db_host']
db_port =os.environ['db_port']
db_database = os.environ['db_database']
bucket_name = os.environ['bucket_name']

def convert_to_sql_date_range(input_month, join_table):
    
    date_obj = datetime.strptime(input_month, '%Y-%m')
    start_date = date_obj.replace(day=1)
    
    if date_obj.month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    if join_table:
        return f"""vsd."time_stamp" >= '{start_date_str}' AND vsd."time_stamp" < '{end_date_str}'"""
    
    return f""""time_stamp" >= '{start_date_str}' AND "time_stamp" < '{end_date_str}'"""


def generate_presigned_url(bucket_name, object_key, expiration=3600):

    s3_client = boto3.client('s3')

    content_type, _ = mimetypes.guess_type(object_key)
    
    if not content_type:
        content_type = 'application/octet-stream'

    try:
        response = s3_client.generate_presigned_url('get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key,
                'ResponseContentType': content_type
            },
            ExpiresIn=expiration
        )
        print('response', response)
        return response
    except Exception as e:   
        print('exception', e)
        return None

def create_cognito_user1(user_pool_id, username, user_attributes=None):
    client = boto3.client('cognito-idp')

    try:
        response = client.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=user_attributes,
        DesiredDeliveryMediums=['EMAIL'] 
    )

        print(f"User {username} created. Verification email sent.")
            
        return "success"
    except Exception as e:
        print(f"Error creating user or setting password: {str(e)}")
        return 'user already exists'
  

  
def send_email_via_ses(sender_email, recipient_email, subject, body_html):
    access_key = os.environ['access_key_aivolvex']
    secret_key = os.environ['secret_key_aivolvex']

 
    client = boto3.client('ses', region_name='us-east-1',         
                          aws_access_key_id=access_key,         
        aws_secret_access_key=secret_key) 

    try:
        response = client.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': [
                    recipient_email,
                ]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': body_html,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        print(f"Email sent successfully to {recipient_email}. Message ID: {response['MessageId']}")
    except Exception as e:
        print(f"Error sending email: {str(e)}")

def create_cognito_user(user_pool_id, username, temporary_password, permanent_password, user_attributes=None):
    client = boto3.client('cognito-idp')

    try:
        response = client.admin_create_user(  
            UserPoolId=user_pool_id,
            Username=username,
            TemporaryPassword=temporary_password,
            UserAttributes=user_attributes if user_attributes else [],
            MessageAction='SUPPRESS'  
        )
        print(f"User {username} created successfully.")
    
        client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=permanent_password,  
            Permanent=True  
        )
        print(f"Permanent password set for user {username}.")
        sender_email = os.environ['cognito_ses_email_id']
        recipient_email = username             
        email = username
        subject = 'GMA user credentails'
        body_html = f'<html><body><h1>GMA user credentails:</h1><p>Your username: {email}</p><p>Your password for gma: {permanent_password}</p><p>Happy working!</p></body></html>'
        
        send_email_via_ses(sender_email, recipient_email, subject, body_html)
        
        return "success"
    except Exception as e:
        print(f"Error creating user or setting password: {str(e)}")
        return 'user already exists'
  
def generate_secure_password(length=8):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password) and
            any(c.isupper() for c in password) and
            any(c.isdigit() for c in password) and
            any(c in string.punctuation for c in password)):
            break
    return password

def query_db(query):
    connection = psycopg2.connect(
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port,  # Replace with the SSH tunnel local bind port
        database=db_database
    )                      
    cursor = connection.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    connection.commit()
    cursor.close()
    connection.close()  
    return result

def update_db(query, params):
    connection = psycopg2.connect(
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port,  
        database=db_database
    )                                  
    cursor = connection.cursor()
    cursor.execute(query, params)
    connection.commit()
    cursor.close()
    connection.close() 
    
def insert_db(query,values):
    connection = psycopg2.connect(
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port,  
        database=db_database
    )                                                                            
    cursor = connection.cursor()
    cursor.execute(query,values)
    connection.commit()
    cursor.close()
    connection.close()   
    
def delete_db(query, values):
    connection = psycopg2.connect(
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port,  
        database=db_database   
    )
    
    cursor = connection.cursor()

    cursor.execute(query, values) 
    connection.commit()
    cursor.close()
    connection.close()


def delete_cognito_user(user_pool_id, username, user_id):
    client = boto3.client('cognito-idp')

    try:
        client.admin_delete_user(
            UserPoolId=user_pool_id,
            Username=username
        )
        query = """DELETE FROM "GMA".user_manager
                   WHERE user_id = %s;""" 
        
        params = (user_id,)
        delete_db(query, params)
        return "successfully deleted!"
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return "user dosen't exist"

def get_role(email):
    query = f"""
    SELECT "role"
    FROM "GMA".user_manager
    where email = '{email}';
    """
    db_result = query_db(query)
    
    print('role_fetch', db_result)
    role = ""
    if db_result:
        role = db_result[0][0]
    
    return role
    
def calculate_transcription_cost(total_minutes):

    # cost_tiers = [
    #     (0.02400, 250000),  # T1
    #     (0.01500, 750000),  # T2
    #     (0.01020, 4000000), # T3
    #     (0.00780, 5000000)  # T4
    # ]
    query = """select input_cost, "limit" from "GMA".cost_manager cm 
                where model_type = 'minute' order by s_id;"""
    result = query_db(query)
    print('result:', result)
    cost_tiers = [(float(row[0]), int(row[1])) for row in result]
    
    remaining_minutes = total_minutes
    total_cost = 0.0

    # Sort the tiers in ascending order of limits (smallest to largest)
    cost_tiers.sort(key=lambda x: x[1])

    for cost_per_minute, tier_limit in cost_tiers:
        if remaining_minutes <= 0:
            break
        
        # Calculate minutes applicable for the current tier
        tier_minutes = min(remaining_minutes, tier_limit)
        total_cost += tier_minutes * cost_per_minute
        remaining_minutes -= tier_minutes

    return total_cost
    
def calculate_cost(input_tokens, output_tokens,input_cost,output_cost):
    prompt_cost = input_tokens * input_cost
           
    completion_cost = output_tokens * output_cost    
    print('prompt cost',prompt_cost,'output',completion_cost)
    total_cost = prompt_cost + completion_cost              
    return total_cost 
 
def lambda_handler(event, context):
    
    glue = boto3.client('glue')    
    print('event', event)  
    event_type = event['body']['event_type']  
    # event_type = 'token_cost_analyzer'
    
    input_month = ""
    sql_condition = ""
    try:
        input_month = event['body']['input_month']
        join_table = False
        if event_type in ['category_wise_uploads', 'page_traffic_category_wise']:
            join_table = True
        sql_condition = convert_to_sql_date_range(input_month, join_table)
    except:
        print('No input_month provided.')

    # event_type='generate_temporary_password'
    # event_type = "gma_list_video_summary_details"
      
    if event_type=='video_summary':
        session_id = event['body']['session_id']
        instruction = event['body']['instruction']
        user_name = event['body']['userName']
        email = event['body']['email']
        task_type = event['body']['task_type']
        file_name = ""
        version = event['body']['version']
        s3_key = "s3_key not require"
        if version=='v0':
            s3_key = event['body']['s3_key']
        else:
            query = f"""SELECT input_key
                        FROM "GMA".video_summarization_details
                        where session_id='{session_id}' and version='v0';"""
            version_input = query_db(query)
            s3_key = version_input[0][0]

        
        # session_id = '20241016175225'
        # instruction = "generate a quick video"
        # s3_key = "summary_generator/input/20241016175225/final_video_3.mp4"
        # user_name = 'srinivasa.n@1cloudhub.com'
        # email = 'srinivasa.n@1cloudhub.com'
        
        query = '''INSERT INTO "GMA".video_summarization_details
                   (session_id, input_key, output_key, "time_stamp", instruction, status, user_name, email, version)
                   VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s, %s);'''
        values = (session_id, s3_key, "", instruction, 'In Progress', user_name, email, version)
        
        print(values)  
        insert_db(query, values)

        if len(s3_key)==0:
            s3_key = "no s3 key found"
            
        response = glue.start_job_run(
            JobName='GMA_video_summary_generator',
            Arguments={
                '--session_id': session_id,
                '--s3_path':s3_key,
                '--instruction':instruction,
                '--task_type':task_type,
                '--version':version
            }
        )
    
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Glue job started successfully',
                'JobRunId': response['JobRunId']
            })
        }


    elif event_type == 'get_total_pages':
        email = event['body']['email']
        role = get_role(email)

        sub_query = ""
        if role != 'admin':
            sub_query = f" and email = '{email}'" 
            
        
        total_pages_query = f"""SELECT session_id, input_key, output_key, "time_stamp", status, summary_justification, instruction
                                FROM "GMA".video_summarization_details where version='v0' {sub_query}
                                order by time_stamp desc;"""
        total_pages_result = query_db(total_pages_query)
        total_pages = len(total_pages_result)
        
        return { 'total_pages' : total_pages }
        
    elif event_type=='upload_availability':
        
        email = event['body']['email']
        role = get_role(email)

        query = f"""SELECT status, aspect_ratio_status
                    FROM "GMA".video_summarization_details
                    order by time_stamp desc;"""
        query_result = query_db(query)
        
        valid_status = [
                "completed",
                "video processing failed",
                "Summarizing...",
                "instruction doesn't match with the video",
                "",
                None
            ]
            
        total_available = 0
        for val in query_result:
            if val[0]!=None and val[0].lower() not in valid_status:
                print(val[0]  ," ",val[1])
                total_available += 1 
            if val[1]!=None and val[1].lower() not in valid_status:
                print(val[0]  ," ",val[1])
                total_available += 1 
        
        output = "able" if total_available < 6 else "disable"
        
        return output
            
        
    elif event_type=='gma_list_video_summary_details':
        
        # page_no = 1
        # page_size = 10
         
        page_no = event['body']['page_no']
        page_size = event['body']['limit']
        email = event['body']['email']
        file_name = ""
        file_name_query = ""
        session_id = ""
        # file_name = ''   
        # email = 'srinivasa.n@1cloudhub.com'
        
        try:
            file_name = event['body']['file_name'].lower()
        except:
            print('file name not specified.')
            
        try:
            session_id = event['body']['session_id']
            print('session_id: ', session_id)
        except:
            print('sessionid not found.')

        offset = (page_no - 1) * page_size
        
        
        role = get_role(email)
        
        sub_query = ""
        if role != 'admin':
            sub_query = f"and email = '{email}'"  
            
        if len(session_id)>0:
            sub_query += f""" and session_id = '{session_id}' and version!='v0' ORDER BY "time_stamp" DESC"""
        else:
            sub_query += f""" and version='v0'
            ORDER BY "time_stamp" DESC
            LIMIT {page_size}
            OFFSET {offset};
            """
              
        query = f"""
            SELECT session_id, input_key, output_key, "time_stamp", status, summary_justification, instruction,email,transcribe, aspect_ratio_url, aspect_ratio_status, version
            FROM "GMA".video_summarization_details
            WHERE input_key ILIKE '%{file_name}%' {sub_query}
        """

        db_result = query_db(query)
        print('db_result',db_result)
                                
        db_formatted_output = []
           
        if db_result:
        
            for result in db_result:  
                
                temp_dict = {}
                temp_dict['session_id'] = result[0]
                temp_dict['input_key'] = generate_presigned_url(bucket_name, result[1])
                temp_dict['output_key'] = generate_presigned_url(bucket_name, result[2])
                temp_dict['time_stamp'] = str(result[3])
                temp_dict['status'] = result[4]
                temp_dict['summary_justification'] = str(result[5])
                temp_dict['instruction'] = str(result[6])   
                temp_dict['file_name'] = result[1].strip().split('/')[-1]
                temp_dict['email'] = str(result[7])
                temp_dict['transcribe'] = result[8]
                temp_dict['aspect_ratio_url'] = None
                try:
                    temp_dict['aspect_ratio_url'] = generate_presigned_url(bucket_name, result[9])
                except:
                    temp_dict['aspect_ratio_url'] = None
                temp_dict['aspect_ratio_status'] = result[10]
                temp_dict['version'] = result[11]
                   
                db_formatted_output.append(temp_dict)
                
        print(db_formatted_output)
        return json.loads(json.dumps({'output': db_formatted_output}))
        
    elif event_type == "user_list":
        query = """SELECT email, category, "role", user_id, working_user, user_name, verification
                    FROM "GMA".user_manager;"""
                    
        db_result = query_db(query)
        print('db_result',db_result)
        
        user_list = []
        
        if db_result:
    
        
            for val in db_result:
                temp_dict = {
                    "email": val[0],
                    "given_name": val[1],
                    "profile": val[2],
                    "unique_id" : val[3],
                    "working_user": val[4],
                    "name": val[5],
                    "verification": val[6]
                }
                user_list.append(temp_dict)
            
        return user_list
        
    elif event_type == "add_user_detail":
        
        email = event['body']['email']
        role = event['body']['profile']
        user_id = event['body']['unique_id']
        working_user = event['body']['working_user']
        category = event['body']['given_name']
        user_name = event['body']['name']
          
        
        # email = 'srinivasa.n@1cloudhub.com'
        # role = 'admin'
        # user_id = '892002820'
        # working_user = 'srinivasa.n@1cloudhub.com'
        # category = 'Technical'
        # user_name = 'srinivasa n'
        
        user_pool_id = os.environ['user_pool_id'] 
        temporary_password = 'TempP@ssw0rd'
        permanent_password = generate_secure_password()
        print(f"Generated Password: {permanent_password}")

        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'given_name', 'Value': category} ,
            {'Name': 'name', 'Value': user_name} ,
            {'Name': 'profile', 'Value': role} ,
            {'Name': 'email_verified', 'Value': 'true'} 
        ] 
        
        # user_add_status = create_cognito_user(user_pool_id, email, user_attributes)
        user_add_status = create_cognito_user(user_pool_id, email, temporary_password, permanent_password, user_attributes)
        if 'success' in str(user_add_status):
            user_add_status = "User added successfully!"
            query = """
                INSERT INTO "GMA".user_manager
                (email, category, "role", user_id, working_user, user_name, created_at, verification)
                VALUES(%s, %s, %s, %s, %s, %s, now(),%s);
            """   
            values = (email, category, role, user_id, working_user, user_name, 'not verified')
            print(values)
            insert_db(query,values)
           
        return {
            "status":user_add_status
        }
            
    elif event_type == "edit_user_detail":

        email = event['body']['email']
        role = event['body']['profile']
        user_id = event['body']['unique_id']
        working_user = event['body']['working_user']
        category = event['body']['given_name']
        user_name = event['body']['name']
        
        
        status = "successfully updated!"
        try:
            
            client = boto3.client('cognito-idp')

            user_pool_id = os.environ['user_pool_id'] 
            username = email
            try:
                attributes_to_update = [
                    {
                        'Name': 'profile',  
                        'Value': role
                    }
                ]
                
                response = client.admin_update_user_attributes(
                    UserPoolId=user_pool_id,
                    Username=username,
                    UserAttributes=attributes_to_update
                )
            
                print("Update response:", response)
            except:
                print('not updated user pool!')
                
            query = """update "GMA".user_manager set email  = %s, category = %s, role=%s, user_id=%s, working_user=%s, user_name=%s
                        where user_id = %s;"""
                        
            params = (email,category, role,user_id,working_user,user_name,user_id)
            update_db(query, params)
            status = "successfully updated!"
        except Exception as e:
            status = "unable to update"
            
        return {
            "status": "successfully updated!"
        }

    elif event_type == "delete_user_detail":

        user_id = event['body']['id']
        # user_id = "20241112105005"
        user_pool_id = os.environ['user_pool_id'] 
        username = ""
        
        try:
            query = f"""
                SELECT email, user_id
                FROM "GMA".user_manager where user_id='{user_id}';"""
            db_result = query_db(query)
            print('db_result',db_result)
            
            if db_result:
                username = db_result[0][0]       
                print('user_name', username)
        except:
            username = ""
            
        delete_user_status = delete_cognito_user(user_pool_id, username, user_id)
            
        return {
            "status": delete_user_status 
        }
        
    elif event_type == "get_category_types":
        return {
            "categories" :["Technical", "Business"]
        }
        
    elif event_type == 'page_traffic_category_wise':
        
        sub_query = ""
        if len(sql_condition)>0:
            sub_query = f" and {sql_condition} "

        query = f""" SELECT um.category, COUNT(vsd.id), DATE_TRUNC('day', vsd."time_stamp") AS time_range
                    FROM "GMA".video_summarization_details AS vsd
                    INNER JOIN "GMA".user_manager AS um
                    ON vsd.email = um.email
                    WHERE vsd."time_stamp" >= DATE_TRUNC('day', CURRENT_DATE) - INTERVAL '6 Months' {sub_query}
                    GROUP BY DATE_TRUNC('day', vsd."time_stamp"), um.category
                    ORDER BY time_range
                    """
                    
        db_result = query_db(query)
        print('db_result', db_result)
        category_wise_count = []
        
        if db_result:
            for val in db_result:
                if val[0] is not None and val[1] is not None and val[2] is not None:
                    temp_dict = {
                        "category": val[0],
                        "value": val[1],
                        "time_range": str(val[2].isoformat()).split('T')[0]
                    }
                    category_wise_count.append(json.dumps(temp_dict))
            
        return category_wise_count
    
            
    
    elif event_type == 'category_wise_uploads':
        
        sub_query = ""
        if len(sql_condition)>0:
            sub_query = f" where {sql_condition} "

        
        query = f"""SELECT um.category, count(vsd.id )
                    FROM "GMA".video_summarization_details AS vsd
                    inner JOIN "GMA".user_manager AS um
                    ON vsd.user_name  = um.email 
                    {sub_query}
                    GROUP BY um.category;
                    """   
                    
        db_result = query_db(query)
        print('db_result',db_result)
        category_wise_count = []
        
        if db_result:
            for val in db_result:
                if val[0] is not None and val[1] is not None:
                    temp_dict = {
                        "category": val[0],
                        "value" : val[1]
                    }
                    category_wise_count.append(json.dumps(temp_dict))
                    
            
        
        return category_wise_count
        
        
    elif event_type == "token_cost_montly_wise":
        
        sub_query = ""
        if len(sql_condition)>0:
            sub_query = f"where {sql_condition} "

        query = f"""SELECT 
                    EXTRACT(YEAR FROM "time_stamp") AS year,
                    EXTRACT(MONTH FROM "time_stamp") AS month,
                    SUM("llm_cost"::numeric) AS llm_cost
                FROM 
                    "GMA".video_summarization_details
                {sub_query}
                GROUP BY 
                    EXTRACT(YEAR FROM "time_stamp"), EXTRACT(MONTH FROM "time_stamp")
                ORDER BY 
                    year, month 
                LIMIT 6;
                """
        db_result = query_db(query)
        print('db_result',db_result)
        token_cost_montly_wise = []
        
        if db_result:
            for val in db_result:     
                if val[0] is not None and val[1] is not None and val[2] is not None:
                    temp_dict = {
                        "month": str(val[0])+"/"+str(val[1]),
                        "cost": str(val[2])
                    }
                    token_cost_montly_wise.append(json.dumps(temp_dict))
                    
        return token_cost_montly_wise
        
    elif event_type == 'topic_wise_uploads':
        
        sub_query = ""
        if len(sql_condition)>0:
            sub_query = f" where {sql_condition}"

        query = f"""select topics, count(id) from "GMA".video_summarization_details vsd {sub_query} group by topics;"""
                    
        db_result = query_db(query)
        print('db_result',db_result)
        topic_wise_count = []
        
        if db_result:
            for val in db_result:
                if val[0] is not None and val[1] is not None:
                    temp_dict = {
                        "topic": val[0],
                        "value" : val[1]
                    }   
                    topic_wise_count.append(json.dumps(temp_dict))
                    
        return topic_wise_count
        
    elif event_type == 'get_page_traffic':
        
        # time_range = ['2024.11.06', '2024.11.07']    

        try:
            time_range = event['body']['time_range']


#             query = f"""
#                 SELECT 
#                     DATE_TRUNC('day', "time_stamp") AS time_range,
#                     COUNT(id) AS daily_uploads
#                 FROM 
#                     "GMA".video_summarization_details
#                 WHERE 
#                     "time_stamp" BETWEEN '{time_range[0]}' AND '{time_range[1]}'
#                 GROUP BY 
#                     DATE_TRUNC('day', "time_stamp")
#                 ORDER BY 
#                     time_range;
# """


            start_date = datetime.strptime(time_range[0], '%Y.%m.%d')
            end_date = datetime.strptime(time_range[1], '%Y.%m.%d')
        
            end_date = end_date + timedelta(days=1)
        
            time_range[1] = end_date.strftime('%Y.%m.%d')
        
            print("Adjusted time range:", time_range)
        
            query = f"""
                SELECT 
                    DATE_TRUNC('day', "time_stamp") AS time_range,
                    COUNT(id) AS daily_uploads
                FROM 
                    "GMA".video_summarization_details
                WHERE 
                    "time_stamp" >= '{time_range[0]}' AND "time_stamp" < '{time_range[1]}'
                GROUP BY 
                    DATE_TRUNC('day', "time_stamp")
                ORDER BY 
                    time_range;
            """
            print("Query:", query)

        except:
            sub_query = ""
            if len(sql_condition)>0:
                sub_query = f" {sql_condition}"
            else:
                sub_query = """"time_stamp" >= DATE_TRUNC('day', CURRENT_DATE) - INTERVAL '6 months'"""
            
            
            query = f'''SELECT 
                DATE_TRUNC('day', "time_stamp") AS time_range,
                COUNT(id) AS daily_uploads
            FROM 
                "GMA".video_summarization_details
            WHERE 
                {sub_query}
            GROUP BY 
                DATE_TRUNC('day', "time_stamp")
            ORDER BY 
                time_range;
            '''
        
        db_result = query_db(query)
        print('db_result', db_result)
        
        time_range_details = []
        
        if db_result:
            for val in db_result:
                if val[0] is not None and val[1] is not None:
                    temp_dict = {
                        "time_range": val[0].strftime('%Y-%m-%d'), 
                        "upload_count": val[1]
                    }
                    time_range_details.append(temp_dict)
            
    
        return time_range_details
                
    elif event_type == "api_cost_montly_wise":
        
            sub_query = ""
            if len(sql_condition)>0:
                sub_query = f"where {sql_condition}"

            query = f"""SELECT 
                        EXTRACT(YEAR FROM "time_stamp") AS year,
                        EXTRACT(MONTH FROM "time_stamp") AS month,
                        SUM("duration"::numeric) AS minutes
                    FROM 
                        "GMA".video_summarization_details
                    {sub_query}
                    GROUP BY 
                        EXTRACT(YEAR FROM "time_stamp"), EXTRACT(MONTH FROM "time_stamp")
                    ORDER BY    
                        year, month
                    LIMIT 6;
                    """
            db_result = query_db(query)
            print('db_result',db_result)
            transcribe_cost_montly_wise = []
            
            if db_result:
                for val in db_result:   
                    if val[0] is not None and val[1] is not None and val[2] is not None:
                        temp_dict = {
                            "month": str(val[0])+"/"+str(val[1]),
                            "cost": str(calculate_transcription_cost(float(val[2])))  
                        }
                        transcribe_cost_montly_wise.append(json.dumps(temp_dict))
                           
            return transcribe_cost_montly_wise
            
            
    elif event_type == 'generate_temporary_password':
    
        status = "success"
        username = event['body']['email']
        # username = 'srinivasa.n@1cloudhub.com'
        user_pool_id = os.environ['user_pool_id'] 
        
        cognito_client = boto3.client('cognito-idp', 'ap-southeast-1')
        try:
            response = cognito_client.admin_get_user(
                UserPoolId=user_pool_id,  # Your Cognito User Pool ID
                Username=username  # The username of the user whose attributes you want to get
            )
            user_attributes = response['UserAttributes']
            new_user_attributes = []
            for attribute in user_attributes:
                if attribute['Name'] != 'sub':  # Exclude the 'sub' attribute
                    new_user_attributes.append({'Name': attribute['Name'], 'Value': attribute['Value']})
    
            cognito_client.admin_delete_user(
                UserPoolId=user_pool_id,
                Username=username
            )
            time.sleep(3)
            
            cognito_client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=username,
                UserAttributes=new_user_attributes,
                DesiredDeliveryMediums=['EMAIL'] 
            )
            status = 'success'
        except Exception as e:
            status = 'failed'
            print(e)
            
        return status
    
    elif event_type == 'verification_status':
        email = event['body']['email']
        # try:
        query = """UPDATE "GMA".user_manager
                   SET verification = %s
                   where email=%s"""
                   
        params = ('success', email)
        update_db(query, params)
        # except Exception as e:
        #     print(e)
        
    elif event_type == 'current_verfication_status':
        email = event['body']['email']
        
        query = f"""select verification from "GMA".user_manager where email = '{email}';"""
        
        db_result = query_db(query)
        print('verfication status:', db_result)
        
        status = "unknown"
        if db_result:
            status = db_result[0][0]
            
        return status
        
    elif event_type == 'aspect_ratio_enhancement':

        session_id = event['body']['session_id']
        s3_key = event['body']['s3_key']
        instruction = event['body']['instruction']    
        task_type = event['body']['task_type']    
        version = event['body']['version']

        response = glue.start_job_run(
            JobName='GMA_video_summary_generator',
            Arguments={
                '--session_id': session_id,
                '--s3_path':s3_key,
                '--instruction':instruction,
                '--task_type':task_type,
                '--version':version  
            }
        )
        query = f'''update "GMA".video_summarization_details set aspect_ratio_status  = %s
                    where session_id = %s and version = %s;'''
        params = ('Initiated..',session_id, version)
        update_db(query, params)
    
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Glue job started successfully',
                'JobRunId': response['JobRunId']
            })
        }
    
    elif event_type == 'version_finder':
        session_id = event['body']['session_id']
        
        query = f"""
            SELECT session_id, input_key, output_key, "time_stamp", status, summary_justification, instruction,email,transcribe, aspect_ratio_url, aspect_ratio_status, version
            FROM "GMA".video_summarization_details
            WHERE session_id = '{session_id}';
        """

        db_result = query_db(query)
        
        return f"v{len(db_result)}"
        
    elif event_type =='token_cost_analyzer':

        client = boto3.client("bedrock-runtime",'us-east-1')
        model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
        llm = BedrockChat(client=client, model_id=model_id)
        
        input_prompt = event['body']['input_prompt']
        output_prompt = event['body']['output_prompt']
        session_id = event['body']['session_id']
        version = event['body']['version']
        
        input_cost = event['body']['input_cost']
        output_cost = event['body']['output_cost']
        
        input_num_tokens = llm.get_num_tokens(input_prompt)
        output_num_tokens = llm.get_num_tokens(output_prompt)
        input_tokens = input_num_tokens
        output_tokens = output_num_tokens
        total_tokens = int(input_tokens) + int(output_tokens)
        cost = calculate_cost(input_tokens, output_tokens,input_cost,output_cost)  
        total_cost = '{:.4f}'.format(cost / 1000) 
        
        query ='''UPDATE "GMA".video_summarization_details
                    SET llm_cost=%s where session_id = %s and version = %s;'''
        values = (str(total_cost), session_id, version)
        update_db(query,values)
        
        return
          
        
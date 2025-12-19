import boto3
import json
import os
from botocore.exceptions import ClientError

INSTANCE_ID = os.environ.get('INSTANCE_ID')
REGION = os.environ.get('REGION', 'us-east-1')

ec2 = boto3.client('ec2', region_name=REGION)


def create_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body, ensure_ascii=False)
    }


def get_instance_info():
    try:
        response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
        instance = response['Reservations'][0]['Instances'][0]
        
        return {
            'state': instance['State']['Name'],
            'public_ip': instance.get('PublicIpAddress'),
            'instance_id': INSTANCE_ID
        }
    except ClientError as e:
        print(f"Error obteniendo información: {e}")
        raise


def start_server(event, context):
    print(f"Iniciando servidor - Instance ID: {INSTANCE_ID}")
    
    try:
        if not INSTANCE_ID:
            return create_response(500, {
                'error': 'INSTANCE_ID no configurado'
            })
        
        instance_info = get_instance_info()
        state = instance_info['state']
        
        print(f"Estado actual: {state}")
        
        if state == 'running':
            return create_response(200, {
                'mensaje': 'Servidor ya está corriendo',
                'ip': instance_info['public_ip'],
                'puerto': 25565,
                'estado': state
            })
        
        if state == 'pending':
            return create_response(202, {
                'mensaje': 'Servidor está arrancando',
                'estado': state
            })
        
        if state == 'stopped':
            print("Iniciando instancia EC2...")
            ec2.start_instances(InstanceIds=[INSTANCE_ID])
            
            print("Esperando a que la instancia esté corriendo...")
            waiter = ec2.get_waiter('instance_running')
            waiter.wait(
                InstanceIds=[INSTANCE_ID],
                WaiterConfig={'Delay': 5, 'MaxAttempts': 40}
            )
            
            instance_info = get_instance_info()
            ip_publica = instance_info['public_ip']
            
            print(f"Instancia iniciada. IP: {ip_publica}")
            
            return create_response(200, {
                'mensaje': 'Servidor iniciado exitosamente',
                'ip': ip_publica,
                'puerto': 25565,
                'estado': 'running',
                'nota': 'Espera 1-2 minutos para que Minecraft esté listo',
                'conexion': f'{ip_publica}:25565'
            })
        
        return create_response(202, {
            'mensaje': f'Instancia en estado: {state}',
            'estado': state
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {
            'error': str(e),
            'mensaje': 'Error al iniciar el servidor'
        })


def stop_server(event, context):
    print(f"Deteniendo servidor - Instance ID: {INSTANCE_ID}")
    
    try:
        if not INSTANCE_ID:
            return create_response(500, {
                'error': 'INSTANCE_ID no configurado'
            })
        
        instance_info = get_instance_info()
        state = instance_info['state']
        
        if state == 'stopped':
            return create_response(200, {
                'mensaje': 'Servidor ya está detenido',
                'estado': state
            })
        
        if state == 'running':
            print("Deteniendo instancia...")
            ec2.stop_instances(InstanceIds=[INSTANCE_ID])
            
            return create_response(200, {
                'mensaje': 'Servidor deteniéndose',
                'estado': 'stopping'
            })
        
        return create_response(202, {
            'mensaje': f'Instancia en estado: {state}',
            'estado': state
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {
            'error': str(e)
        })


def get_status(event, context):
    print(f"Obteniendo estado - Instance ID: {INSTANCE_ID}")
    
    try:
        if not INSTANCE_ID:
            return create_response(500, {
                'error': 'INSTANCE_ID no configurado'
            })
        
        instance_info = get_instance_info()
        
        response_data = {
            'estado': instance_info['state'],
            'instance_id': INSTANCE_ID,
            'region': REGION
        }
        
        if instance_info['public_ip']:
            response_data['ip'] = instance_info['public_ip']
            response_data['puerto'] = 25565
            response_data['conexion'] = f"{instance_info['public_ip']}:25565"
        
        return create_response(200, response_data)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {
            'error': str(e)
        })
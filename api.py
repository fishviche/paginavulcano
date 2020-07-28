from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_required, logout_user, current_user, login_user, current_user

from werkzeug.utils import secure_filename

from bson import json_util
import json
from bson.objectid import ObjectId

from random import random

import os


app = Flask(__name__)

#CONFIGURACIÓN RUTA DE DESCARGAS
UPLOAD_FOLDER = os.path.abspath("./static/uploads/")
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpge"])

#CONECCION CON MONGODB


app.config['MONGO_URI']='mongodb://mongodb:27017/users'
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

mongo = PyMongo(app)


app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER



def allowed_file(filename):

    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


#PARA OBTENER LOS DATOS DE MongoDB 
class datosMongo():
    def __init__(self,tipo,username):

        if tipo == 'masteruser':
            masteruser = mongo.db.users.find_one({"tipo": "masteruser"})
            response = json_util.dumps(masteruser)
            MASTERusuario = json.loads(response)
            self.username = MASTERusuario['username']
            self.password = MASTERusuario['password']

        if tipo == 'cliente':
            cliente = mongo.db.users.find({"tipo": "cliente"})
            response = json.loads(json_util.dumps(cliente))
            DatoCliente=[]
            for h in response:
                if h['username'] == username:
                    DatoCliente = h     
            self.username = DatoCliente['username']
            self.password = DatoCliente['password']
                

#Para saber que tipo de dato es cliente o masteruser
class TipoDato():
    def __init__(self,username):
        DATA = []
        for h in json.loads(json_util.dumps(mongo.db.users.find({"uso": "interno"},{"username": 1, "tipo": 1, "_id": 0}))):
            if username in h['username']:
                DATA = h

        if len(DATA) == 0:        
            self.tipo = False 
        if len(DATA) != 0:
            self.tipo = DATA['tipo']

#para detectar si esta conectado el masteruser
class sesionMasterUser():
    def __init__(self):
        self.estado=False

#variable para usar para las rutas de masterUser
EstadoMasteruser = sesionMasterUser()

#CONFIGURACION PARA EL LOGIN
login_manager = LoginManager()
login_manager.init_app(app)


#CONFIGURACION LOGIN_MANAGER
class User(UserMixin):
    pass

@login_manager.user_loader
def user_loader(username):
    
    tipoDato = TipoDato(username)
    tipo = tipoDato.tipo
    datoMasterUser= datosMongo(tipo, username)
    
    if username not in datoMasterUser.username:
        return

    user = User()
    user.id = username
    return user


#CONFIGURACION DE RUTAS
@app.route('/login')
def login():
    return render_template('index.html')


@app.route('/loginMaster', methods=['POST'])
def loginMaster():
    username = request.form['username']
    password = request.form['password']

    if username is "":
        username = "serviciodesactivado"

    tipoDato = TipoDato(username)
    tipo = tipoDato.tipo
    
    if tipo == 'masteruser':
        datoMasterUser = datosMongo(tipo, None)
        EstadoMasteruser.estado = True

        if username == datoMasterUser.username:
            if password == datoMasterUser.password:
                user = User()
                user.id = username
                login_user(user)
                return redirect(url_for('crearCuenta'))
            else:
                return redirect(url_for('login'))
        else:
            return redirect(url_for('login'))

    if tipo == 'cliente':
        DatoCliente = datosMongo(tipo, username)
        EstadoMasteruser.estado = False

        if username == DatoCliente.username:
            if password == DatoCliente.password:
                user = User()
                user.id = username
                login_user(user)
                return redirect(url_for('get_products'))
            else :
                return redirect(url_for('login'))
        else:
            return redirect(url_for('login'))

    else:
            return redirect(url_for('login'))

#ADMINISTRACIÓN DE CUENTAS
@app.route('/loginMaster/crearCuenta', methods=['GET', 'POST'])
@login_required
def crearCuenta():
    if request.method == 'GET' and EstadoMasteruser.estado:
        EstadoMasteruser.estado = True
        cliente = mongo.db.users.find({"tipo": "cliente"})
        response = json.loads(json_util.dumps(cliente))
        
        return render_template("loginMaster.html", datosClientes = response) 

    elif request.method == 'POST' and EstadoMasteruser.estado:
        username = request.form['username']
        password = request.form['password']
        EstadoMasteruser.estado = True

        #para no añadir usuarios con el mismo nombre
        existing_user = mongo.db.users.find_one({'username': username})
        if existing_user is None:
            mongo.db.users.insert_one({'tipo': 'cliente', 'uso': 'interno', 'username': username, 'password': password})
        
        return redirect(url_for('crearCuenta'))

    else:
        return redirect(url_for('get_products'))

#PARA ELIMANAR UN CLIENTE DE ADMINISTRADOR
@app.route('/eliminarCliente/<id>')
@login_required
def eliminar_Cliente(id):
    if EstadoMasteruser.estado:
        EstadoMasteruser.estado = True
        mongo.db.users.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('crearCuenta'))


#ADMINSTRACION DE LOS CLIENTES
@app.route('/admiProducts', methods=['GET', 'POST'])
@login_required
def get_products():
    if request.method == 'GET':
        respuesta = mongo.db.users.find({'tipo': 'producto'})
        respuestaProcesada = json.loads(json_util.dumps(respuesta))

        #AÑADIENDO PARA LA VISUALIZACION DE CATEGORIÁS
        respuesta1 = mongo.db.users.find({'tipo':'categorias'})
        respuestaProcesada1 = json.loads(json_util.dumps(respuesta1))

        return render_template("admiProducts.html", dataProducts = respuestaProcesada, categorias = respuestaProcesada1)

    if request.method == 'POST':
        #DATOS DEL PRODUCTO
        NombreProduct = request.form['NombreProduct']
        Descripcion = request.form['Descripcion']
        Price = request.form['Price']
        Categoria = request.form['Categorias']
        #DATOS DE LA IMAGEN
                
        mongo.db.users.insert_one({'tipo': 'producto', 
                                    'Nombre': NombreProduct,
                                    'Precio': Price, 
                                    'Descripcion': Descripcion,
                                    'MoreDescripcion': '',
                                    'Categoria': Categoria})
        ImagenProduct = request.files["ImagenProduct"]
          
        #LOGICA PARA EL GUARDADO DE IMAGENES
        if ImagenProduct and allowed_file(ImagenProduct.filename):
            filename = secure_filename(ImagenProduct.filename)
            ImagenProduct.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                            
            #para cambiar el nombre de las imagenes al id
            nombreIMAGE = json.loads(json_util.dumps(mongo.db.users.find_one({'Nombre': NombreProduct,
                                                                        'Descripcion':Descripcion,
                                                                        'Precio': Price,
                                                                        'MoreDescripcion':'',
                                                                        'Categoria': Categoria
                                                                        },
                                                                        {'_id':1})))['_id']['$oid']
            
            ext = ("."+filename.rsplit(".",1)[1])

            nombreFinal = nombreIMAGE + ext
            src = 'static/uploads/'+ filename
            dst = ('static/uploads/'+ nombreFinal)
            os.rename(src,dst)       

            mongo.db.users.update({"_id": ObjectId(nombreIMAGE)},{"$set":{"IDfoto": nombreFinal}})
        

        if ImagenProduct is None:
             return redirect(url_for('get_products'))

        return redirect(url_for('get_products'))

#PARA ELIMINAR LOS PRODUCTOS
@app.route('/deleteProduct/<id>')
@login_required
def delete_product(id):
    mongo.db.users.delete_one({'_id': ObjectId(id)})
    #para eliminar la foto de cada elemento
    deleteFoto(id)
    return redirect(url_for('get_products'))


#PARA EDITAR LOS PRODUCTOS
@app.route('/getProduct/<id>')
@login_required
def get_product(id):
    data = mongo.db.users.find_one({'_id': ObjectId(id)})
    respuesta = json.loads(json_util.dumps(data))
    
    dato = ""
    for imgPRODUCTO in os.listdir("static/uploads"):
        if id == imgPRODUCTO.rsplit(".",1)[0]:
            dato = imgPRODUCTO

    DescriptionDesproceda=""
    if respuesta is not None:
        desciptiondata=respuesta['MoreDescripcion']
        for i in desciptiondata:
            DescriptionDesproceda=DescriptionDesproceda+i+"\r\n"        
    return render_template('editProduct.html',product = respuesta, nombreFoto = dato, MoreDescription=DescriptionDesproceda)



@app.route('/editProduct/<id>', methods=['POST'])
@login_required
def edit_product(id):
    if request.method == 'POST':
        NombreProduct = request.form['NombreProduct']
        Descripcion = request.form['Descripcion']
        Price = request.form['Price']
        MoreDescription = request.form['MoreDescription']

        Editar=str.split(MoreDescription,"\r\n")
        
        mongo.db.users.update_one({'_id': ObjectId(id)},{'$set': {
            'tipo': 'producto',
            'Nombre': NombreProduct,
            'Precio': Price,
            'Descripcion': Descripcion,
            'MoreDescripcion': Editar
        }})

        ImagenProduct = request.files["ImagenProduct"]
          
        #LOGICA PARA EL GUARDADO DE IMAGENES
        if ImagenProduct and allowed_file(ImagenProduct.filename):
            #para eliminar la foto
            deleteFoto(id)
                    
            filename = secure_filename(ImagenProduct.filename)
            ImagenProduct.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            ext = ("."+filename.rsplit(".",1)[1])
            src = ('static/uploads/'+ filename)
            dst = ('static/uploads/'+ id + ext)
            os.rename(src,dst)                        
                
        if ImagenProduct is None:
             return redirect(url_for('get_product', id=id))
             
        return redirect(url_for('get_product', id=id))

#VENTANA PRINCIPAL
@app.route('/', methods=['GET','POST'])
def inicio():
    if request.method == 'GET':
        respuesta = mongo.db.users.find({'tipo': 'producto'})
        respuestaProcesada = json.loads(json_util.dumps(respuesta))
        
        respuesta1 = mongo.db.users.find_one({'tipo':'redesSociales'})
        respuestaProcesada1 = json.loads(json_util.dumps(respuesta1))
        mensaje1=""
        if respuestaProcesada1 is not None:
            whatsapp=respuestaProcesada1['Whatsapp']
            codigoPais="51"
            mensaje="https://api.whatsapp.com/send?phone={}{}&text=hola,%20me%20gustaría%20comprar%20un%20producto"
            mensaje1=mensaje.format(codigoPais,whatsapp)
        
        respuesta2 = mongo.db.users.find_one({'tipo':'infoGeneral'},{'_id': 0, 'tipo': 0})
        respuestaProcesada2 = json.loads(json_util.dumps(respuesta2))
        
        respuesta3 = mongo.db.users.find({'tipo': 'categorias'})
        respuestaProcesada3 = json.loads(json_util.dumps(respuesta3))

        return render_template('ventanaPrincipal.html', dataProducts = reversed(respuestaProcesada), redesInfo=respuestaProcesada1, Whatsapp=mensaje1, infoGeneral=respuestaProcesada2, categorias = respuestaProcesada3)

@app.route('/producto/<id>',methods=['GET','POST'])
def mostrarProducto(id):
    if request.method == 'GET':
        respuesta = mongo.db.users.find_one({'_id': ObjectId(id)})
        respuestaProcesada = json.loads(json_util.dumps(respuesta))

        respuesta1 = mongo.db.users.find_one({'tipo':'redesSociales'})
        respuestaProcesada1 = json.loads(json_util.dumps(respuesta1))

        mensaje1=""
        if respuestaProcesada1 is not None:
            whatsapp=respuestaProcesada1['Whatsapp']
            nombreproducto=respuestaProcesada['Nombre']
            codigoPais="51"
            mensaje="https://api.whatsapp.com/send?phone={}{}&text=hola,%20me%20gustaría%20comprar%20el%20producto%20{}"
            mensaje1=mensaje.format(codigoPais,whatsapp,nombreproducto)

        return render_template('mostrarProducto.html',infoProducto = respuestaProcesada, Whatsapp=mensaje1)

@app.route('/contactos', methods=['POST'])
def contactos():
    if request.method == 'POST':
        #DATOS DESDE DE CONTACTO DE VENTANAPRINCIPAL
        NombreContacto = request.form['Nombre']
        EmailContacto = request.form['Email']
        NumeroContacto = request.form['Celular']
        MensajeContacto = request.form['Mensaje']

        MensajeProcesado = str.split(MensajeContacto,'\r\n')

        numeroRandom=random()   #Por si ponen datos iguales
        
        #AÑADIR A LA BASE DE DATOS
        mongo.db.users.insert_one({'tipo': 'contacto', 'Nombre': NombreContacto,
        'Email': EmailContacto,'Numero': NumeroContacto, 'Mensaje': MensajeProcesado,'Random': numeroRandom})

        return redirect(url_for('inicio'))




@app.route('/contactosRecibidos', methods=['GET'])
@login_required
def contactosRecibidos():
    if request.method == 'GET':
        respuesta = mongo.db.users.find({'tipo':'contacto'})
        respuestaProcesada = json.loads(json_util.dumps(respuesta))
        return render_template("contactos.html", dataProducts = respuestaProcesada)


@app.route('/deleteContact/<id>',methods=['GET'])
@login_required
def deleteContact(id):
    if request.method == 'GET':
        mongo.db.users.delete_one({'_id': ObjectId(id)})
        return redirect(url_for('contactosRecibidos'))


@app.route('/ConfigRedesSociales', methods=['GET','POST'])
@login_required
def confRedes():
    if request.method == 'GET':
        respuesta = mongo.db.users.find_one({'tipo':'redesSociales'})
        respuestaProcesada = json.loads(json_util.dumps(respuesta))
        return render_template('redesSociales.html', datos = respuestaProcesada)

    if request.method == 'POST':
        NombreTienda = request.form['Tienda']
        Facebook = request.form['Facebook']
        Instagram = request.form['Instagram']
        Whatsapp = request.form['Whatsapp']

        mongo.db.users.delete_one({'tipo': 'redesSociales'})
        #AÑADIR A LA BASE DE DATOS
        mongo.db.users.insert_one({'tipo': 'redesSociales', 'NombreTienda': NombreTienda,
        'Facebook': Facebook,'Instagram': Instagram, 'Whatsapp': Whatsapp})
        return redirect(url_for('confRedes'))   

@app.route('/infoGeneral',methods=['GET', 'POST'])
@login_required
def infoGeneral():
    if request.method == 'GET':
        respuesta = mongo.db.users.find_one({'tipo':'infoGeneral'})
        respuestaProcesada = json.loads(json_util.dumps(respuesta))
        return render_template('infoGeneral.html', datos = respuestaProcesada)

    if request.method == 'POST':
        Ubicacion = request.form['Ubicacion']
        Telefono = request.form['Telefono']
        GoogleMaps = request.form['GoogleMaps']
        Correo = request.form['Correo']

        mongo.db.users.delete_one({'tipo': 'infoGeneral'})
        #Añadir datos
        mongo.db.users.insert_one({'tipo': 'infoGeneral', 'Ubicacion': Ubicacion, 'GoogleMaps': GoogleMaps,
                                    'Telefono': Telefono, 'Correo': Correo})
        return redirect(url_for('infoGeneral'))

#CREACION Y ELIMNACION DE CATEGORIAS
@app.route('/NewCategoria', methods=['POST'])
@login_required
def NewCategoria():
    
    if request.method == 'POST':
        NewCategoria = request.form['Categoria']
        mongo.db.users.insert_one({'tipo': 'categorias','NewCategoria': NewCategoria})

        return redirect(url_for('get_products'))
#ELIMINAR CATEGORIAS
@app.route('/deleteCategoria/<id>', methods=['GET'])
@login_required
def deleteCategoria(id):
    if request.method == 'GET':
        mongo.db.users.delete_one({'_id': ObjectId(id)})
        return redirect(url_for('get_products'))

#BUSQUEDA DE PRODUCTOS
@app.route('/buscarProducto/<id>', methods=['GET'])
def buscarProducto(id):
    if request.method == 'GET':
        respuesta = mongo.db.users.find({'Categoria': id})
        respuestaProcesada = json.loads(json_util.dumps(respuesta))
        
        respuesta1 = mongo.db.users.find_one({'tipo':'redesSociales'})
        respuestaProcesada1 = json.loads(json_util.dumps(respuesta1))
        mensaje1=""
        if respuestaProcesada1 is not None:
            whatsapp=respuestaProcesada1['Whatsapp']
            codigoPais="51"
            mensaje="https://api.whatsapp.com/send?phone={}{}&text=hola,%20me%20gustaría%20comprar%20un%20producto"
            mensaje1=mensaje.format(codigoPais,whatsapp)
        
        respuesta2 = mongo.db.users.find_one({'tipo':'infoGeneral'},{'_id': 0, 'tipo': 0})
        respuestaProcesada2 = json.loads(json_util.dumps(respuesta2))
        
        respuesta3 = mongo.db.users.find({'tipo': 'categorias'})
        respuestaProcesada3 = json.loads(json_util.dumps(respuesta3))

        return render_template('ventanaPrincipal.html', dataProducts = reversed(respuestaProcesada), redesInfo=respuestaProcesada1, Whatsapp=mensaje1, infoGeneral=respuestaProcesada2, categorias = respuestaProcesada3)





#PARA CERRAR SESION LA CUENTA
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for('login'))


def deleteFoto(id):
    for foto in os.listdir("static/uploads"):
        if id == foto.rsplit(".",1)[0]:
            extencion = ("."+foto.rsplit(".",1)[1])
            os.remove("static/uploads/"+id+extencion)

if __name__ == '__main__':
    app.secret_key = 'mysecretkey'
    app.run(port=5005, debug=True)

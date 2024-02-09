from flask import Blueprint, request, jsonify
from datetime import datetime
from .models import Chambre, Reservation
from .database import db
from sqlalchemy import and_, not_
SQLAlchemyError = db.exc.SQLAlchemyError

main = Blueprint('main', __name__)

@main.route('/api/chambres/disponibles', methods=['GET'])
def get_available_rooms():
    date_arrivee = request.args.get('date_arrivee')
    date_depart = request.args.get('date_depart')

    if not date_arrivee or not date_depart:
        return jsonify({'error': 'Please provide both date_arrivee and date_depart parameters'}), 400

    subquery = db.session.query(Reservation.id_chambre).filter(
        and_(
            Reservation.date_arrivee < date_depart,
            Reservation.date_depart > date_arrivee
        )
    ).subquery()

    available_rooms = Chambre.query.filter(
        ~Chambre.id.in_(subquery)
    ).all()

    results = [
        {
            'id': room.id,
            'numero': room.numero,
            'type': room.type,
            'prix': room.prix
        } for room in available_rooms
    ]

    return jsonify(results)

@main.route('/api/reservations', methods=['POST'])
def create_reservation():
    try:
        data = request.get_json()
        id_client = data['id_client']
        id_chambre = data['id_chambre']
        date_arrivee = datetime.strptime(data['date_arrivee'], '%Y-%m-%d')
        date_depart = datetime.strptime(data['date_depart'], '%Y-%m-%d')
    except (TypeError, KeyError, ValueError):
        return jsonify({'error': 'Invalid request data'}), 400

    overlapping_reservations = Reservation.query.filter(
        Reservation.id_chambre == id_chambre,
        not_(
            (Reservation.date_depart <= date_arrivee) | (Reservation.date_arrivee >= date_depart)
        )
    ).first()

    if overlapping_reservations:
        return jsonify({'error': 'Chambre non disponible pour les dates sélectionnées'}), 400

    try:
        new_reservation = Reservation(
            id_client=id_client,
            id_chambre=id_chambre,
            date_arrivee=date_arrivee,
            date_depart=date_depart,
            statut='confirmée'
        )
        db.session.add(new_reservation)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred', 'message': str(e)}), 500

    return jsonify({'success': True, 'message': 'Réservation créée avec succès.'}), 201
  
@main.route('/api/reservations/<int:id>', methods=['DELETE'])
def cancel_reservation(id):
    reservation = Reservation.query.get(id)
    if not reservation:
        return jsonify({'error': 'Reservation not found'}), 404

    try:
        db.session.delete(reservation)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Réservation annulée avec succès.'}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred', 'message': str(e)}), 500
      
@main.route('/api/chambres', methods=['POST'])
def add_room():
    try:
        data = request.get_json()
        new_room = Chambre(numero=data['numero'], type=data['type'], prix=data['prix'])
        db.session.add(new_room)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Chambre ajoutée avec succès.'}), 201
    except (TypeError, KeyError):
        return jsonify({'error': 'Missing or invalid data in request'}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred', 'message': str(e)}), 500

@main.route('/api/chambres/<int:id>', methods=['PUT'])
def update_room(id):
    room = Chambre.query.get(id)
    if not room:
        return jsonify({'error': 'Chambre not found'}), 404

    try:
        data = request.get_json()
        room.numero = data.get('numero', room.numero)
        room.type = data.get('type', room.type)
        room.prix = data.get('prix', room.prix)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Chambre mise à jour avec succès.'}), 200
    except (TypeError, KeyError):
        return jsonify({'error': 'Missing or invalid data in request'}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred', 'message': str(e)}), 500

@main.route('/api/chambres/<int:id>', methods=['DELETE'])
def delete_room(id):
    room = Chambre.query.get(id)
    if not room:
        return jsonify({'error': 'Chambre not found'}), 404

    try:
        db.session.delete(room)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Chambre supprimée avec succès.'}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred', 'message': str(e)}), 500


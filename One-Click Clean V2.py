import bpy

def cleanup_cad_scene_with_strays():
    # --- CONFIGURATION ---
    text_col_name = "CAD_Text"
    curve_col_name = "CAD_Curves"
    stray_col_name = "CAD_Stray_Geometry"
    
    # PROTECTED COLLECTIONS:
    # Objects in these collections will be IGNORED (not unparented, not moved).
    protected_collections = ["Walls", "Stairs", "Doors", "Room_Holders", "Walls_3D"] 

    # --- HELPER FUNCTIONS ---
    def get_or_create_collection(name):
        if name in bpy.data.collections:
            return bpy.data.collections[name]
        else:
            new_col = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(new_col)
            return new_col

    # --- MAIN EXECUTION ---
    text_col = get_or_create_collection(text_col_name)
    curve_col = get_or_create_collection(curve_col_name)
    stray_col = get_or_create_collection(stray_col_name)
    
    # Lists for sorting
    empties_to_delete = []
    text_to_move = []
    curves_to_move = []
    strays_to_move = []
    
    print("Scanning objects...")
    
    # We iterate over scene objects
    for obj in bpy.context.scene.objects:
        
        # --- SAFETY CHECK ---
        # Check if object is in a protected collection (Your clean walls/rigs)
        is_protected = False
        for col in obj.users_collection:
            if col.name in protected_collections:
                is_protected = True
                break
        
        if is_protected:
            continue

        # --- STEP 0: UNPARENT (KEEP TRANSFORM) ---
        # This ensures that if we delete the parent Empty later, 
        # the child keeps its current size/position and becomes independent.
        if obj.parent:
            # We copy the current world matrix (visual transform)
            current_matrix = obj.matrix_world.copy()
            # We clear the parent
            obj.parent = None
            # We re-apply the matrix so it doesn't jump
            obj.matrix_world = current_matrix

        # --- CATEGORIZE ---
        if obj.type == 'EMPTY':
            empties_to_delete.append(obj)
            
        elif obj.type == 'FONT':
            text_to_move.append(obj)
            
        elif obj.type == 'CURVE':
            curves_to_move.append(obj)
            
        elif obj.type == 'MESH':
            # This captures the "leftover walls" from CAD
            strays_to_move.append(obj)
            
    # --- ACTION ---
    
    # 1. Delete Empties
    print(f"Deleting {len(empties_to_delete)} Empties...")
    for obj in empties_to_delete:
        # Safety: Ensure we don't delete something that is still a parent 
        # (though we just unparented everything, so this should be safe)
        bpy.data.objects.remove(obj, do_unlink=True)
        
    # 2. Move Text
    print(f"Moving {len(text_to_move)} Text objects...")
    for obj in text_to_move:
        for old_col in obj.users_collection:
            old_col.objects.unlink(obj)
        text_col.objects.link(obj)
        
    # 3. Move Curves
    print(f"Moving {len(curves_to_move)} Curve objects...")
    for obj in curves_to_move:
        for old_col in obj.users_collection:
            old_col.objects.unlink(obj)
        curve_col.objects.link(obj)

    # 4. Move Strays (Meshes)
    print(f"Quarantining {len(strays_to_move)} Stray Meshes...")
    for obj in strays_to_move:
        for old_col in obj.users_collection:
            old_col.objects.unlink(obj)
        stray_col.objects.link(obj)

    print("Cleanup Complete. The sanctuary is clean.")

# Run it
cleanup_cad_scene_with_strays()
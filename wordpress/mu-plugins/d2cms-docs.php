<?php
/*----------  DOCS POST TYPE  ----------*/
add_action('init', function() {
	register_post_type('doc', array(
		'labels' => array(
			'name' => 'Docs',
			'singular_name' => 'Doc',
			'menu_name' => 'Docs',
			'all_items' => 'All Docs',
			'edit_item' => 'Edit Doc',
			'view_item' => 'View Doc',
			'view_items' => 'View Docs',
			'add_new_item' => 'Add New Doc',
			'new_item' => 'New Doc',
			'parent_item_colon' => 'Parent Doc:',
			'search_items' => 'Search Docs',
			'not_found' => 'No docs found',
			'not_found_in_trash' => 'No docs found in Trash',
			'archives' => 'Doc Archives',
			'attributes' => 'Doc Attributes',
			'insert_into_item' => 'Insert into doc',
			'uploaded_to_this_item' => 'Uploaded to this doc',
			'filter_items_list' => 'Filter docs list',
			'filter_by_date' => 'Filter docs by date',
			'items_list_navigation' => 'Docs list navigation',
			'items_list' => 'Docs list',
			'item_published' => 'Doc published.',
			'item_published_privately' => 'Doc published privately.',
			'item_reverted_to_draft' => 'Doc reverted to draft.',
			'item_scheduled' => 'Doc scheduled.',
			'item_updated' => 'Doc updated.',
			'item_link' => 'Doc Link',
			'item_link_description' => 'A link to a doc.',
		),
		'public' => true,
		'hierarchical' => true,
		'show_in_rest' => true,
		'rest_base' => 'docs',
		'menu_position' => 8,
		'menu_icon' => 'dashicons-media-document',
		'supports' => array(
			0 => 'title',
			1 => 'editor',
			2 => 'custom-fields',
			3 => 'page-attributes',
		),
		'taxonomies' => array(
			0 => 'post_tag',
		),
		'rewrite' => array(
			'slug' => 'docs',
		),
		'delete_with_user' => false,
	));

    register_post_meta('doc', 'document_key', array(
        'type' => 'string',
        'single' => true,
        'show_in_rest' => true,
    ));

    register_post_meta('doc', 'document_hash', array(
        'type' => 'string',
        'single' => true,
        'show_in_rest' => true,
    ));

    /**
	 * Allow filtering docs by meta_key/meta_value via the REST API.
     * WordPress drops unrecognised query params before they reach WP_Query,
     * so we must explicitly pass them through here.
	 */
    add_filter('rest_doc_query', function($args, $request) {
        $meta_key = $request->get_param('meta_key');
        if ($meta_key) {
            $args['meta_key']   = sanitize_key($meta_key);
            $args['meta_value'] = sanitize_text_field($request->get_param('meta_value') ?? '');
        }
        return $args;
    }, 10, 2);
});


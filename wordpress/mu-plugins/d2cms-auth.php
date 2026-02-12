<?php
/**
 * Plugin Name: D2CMS Dev Token Auth
 * Description: Minimal utility to inject bearer token auth into WordPress.
 */

add_filter('determine_current_user', function($userId) {
    $devToken = getDevToken();
    $devUser = getDevUser();

    if (!$devToken) {
        return $userId;
    }

    $header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    if (strpos($header, 'Bearer') !== 0) {
        return $userId;
    }

    $providedToken = trim(substr($header, 7));
    if (!hash_equals($devToken, $providedToken)) {
        return $userId;
    }

    $user = get_user_by('login', $devUser);

    return !$user ? $userId : (int) $user -> ID;
}, 20);

function getDevUser() {
    return getenv('D2CMS_WP_API_USER');
}

function getDevToken() {
    return getenv('D2CMS_WP_DEV_TOKEN');
}